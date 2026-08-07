import shutil
import subprocess
from pathlib import Path

import bpy

from app.camera import CameraAnimator
from app.config import PipelineSettings
from app.geometry import TrackBuilder
from app.materials import MaterialFactory
from app.progress import (
    Cancelled,
    CancellationToken,
    Phase,
    Reporter,
    cancel_on_signal,
    clear_partial_output,
    progress_iter,
    render_progress,
)
from app.render import RenderSetup
from app.scene import SceneSetup


class RailwayVideoPipeline:
    """Coordinates all generation services into one execution flow."""

    def __init__(
        self,
        settings: PipelineSettings,
        reporter: Reporter | None = None,
        token: CancellationToken | None = None,
    ) -> None:
        self.settings = settings
        self.reporter = reporter or Reporter()
        self.token = token or CancellationToken()
        self.geometry = settings.geometry
        self.scene_setup = SceneSetup(settings.environment)
        self.render_setup = RenderSetup(settings)
        self.material_factory = MaterialFactory(settings.appearance)
        self.track_builder = TrackBuilder(
            settings, self.material_factory, reporter=self.reporter
        )
        self.camera_animator = CameraAnimator(settings)

    def run(self) -> None:
        """Build and render, reporting progress and honouring cancellation.

        Cancellation is checked between phases rather than polled inside them:
        a phase is a unit of work that is cheaper to repeat than to unwind.
        """
        with cancel_on_signal(self.token):
            try:
                self._run()
            except Cancelled:
                removed = clear_partial_output(self.settings.output_dir)
                self.reporter.cancelled(
                    f"Cancelled; removed {len(removed)} partial file(s).",
                    removed=len(removed),
                )
                raise

    def _run(self) -> None:
        # Clear anything an earlier run of this name left behind, however it
        # died. A killed run leaves numbered PNG frames, and ffmpeg assembles
        # by pattern — so leftovers from a longer previous run would be spliced
        # into this one's video. Clearing at the start covers every way a run
        # can end, including the ones no in-process handler can catch.
        clear_partial_output(self.settings.output_dir)

        self.token.check()
        self.reporter.phase_start(Phase.SCENE)
        self.scene_setup.setup_metric_units()
        self.scene_setup.cleanup_scene()
        self.scene_setup.setup_world()

        self.render_setup.apply()
        self.reporter.phase_end(Phase.SCENE)

        self.token.check()
        self.reporter.phase_start(Phase.TRACK)
        self.track_builder.build(self.geometry)
        self.reporter.phase_end(Phase.TRACK)

        self.token.check()
        self.scene_setup.create_lighting()
        camera = self.camera_animator.setup_camera(self.geometry)
        self.camera_animator.animate(camera)
        self.render_setup.apply_eevee_enhancements()

        self.token.check()
        scene = bpy.context.scene
        total_frames = self.settings.render.total_frames
        self.reporter.phase_start(Phase.RENDER, total=total_frames)
        print(f"Setup complete. Starting render to: {scene.render.filepath}")
        with render_progress(scene, desc="Rendering frames...", reporter=self.reporter):
            bpy.ops.render.render(animation=True)
        self.reporter.phase_end(Phase.RENDER)

        self.token.check()
        self.reporter.phase_start(Phase.ENCODE)
        self._finalize_output()
        self.reporter.phase_end(Phase.ENCODE)
        self.reporter.done(
            f"Wrote {self.settings.output_path}", output=self.settings.output_path
        )

    def _finalize_output(self) -> None:
        if not self.render_setup.is_png_fallback:
            return

        output_path = self.render_setup.requested_video_path
        sequence_prefix = self.render_setup.png_sequence_prefix
        if output_path is None or sequence_prefix is None:
            return
        if output_path.suffix.lower() != ".mp4":
            return

        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            print("ffmpeg is not installed; PNG sequence kept and MP4 was not assembled.")
            return

        input_pattern = f"{sequence_prefix}%04d.png"
        cmd = [
            ffmpeg_bin,
            "-y",
            "-framerate",
            str(self.settings.render.fps),
            "-i",
            input_pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
        print(f"Assembling MP4 with ffmpeg to: {output_path}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print("Failed to assemble MP4; PNG sequence kept.")
            if proc.stderr:
                print(proc.stderr.strip().splitlines()[-1])
            return

        frame_glob = f"{sequence_prefix.name}[0-9][0-9][0-9][0-9].png"
        frame_paths = list(Path(sequence_prefix).parent.glob(frame_glob))
        removed = 0
        for frame in progress_iter(
            frame_paths,
            desc="Removing PNG fallback frames",
            total=len(frame_paths),
            unit="frame",
        ):
            frame.unlink(missing_ok=True)
            removed += 1
        print(f"MP4 assembled successfully: {output_path}")
        print(f"Removed {removed} PNG frame files from fallback sequence.")
