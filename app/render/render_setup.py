from pathlib import Path

import bpy

from app.config import PipelineSettings


class RenderSetup:
    """Configures output, frame range, and engine features."""

    def __init__(self, settings: PipelineSettings) -> None:
        self.settings = settings
        self.is_png_fallback = False
        self.requested_video_path: Path | None = None
        self.png_sequence_prefix: Path | None = None

    def apply(self) -> None:
        scene = bpy.context.scene
        total_frames = self.settings.total_frames
        fps = self.settings.fps

        print(
            f"Setting up render settings: {total_frames} frames at {fps} fps "
            f"({total_frames / fps} seconds)..."
        )

        scene.render.engine = self.settings.render_engine
        scene.render.resolution_x = self.settings.resolution_x
        scene.render.resolution_y = self.settings.resolution_y
        scene.render.fps = fps
        scene.frame_start = self.settings.start_frame
        scene.frame_end = total_frames

        output_path = Path(self.settings.output_path)
        if self._configure_video_output(scene):
            self.is_png_fallback = False
            self.requested_video_path = None
            self.png_sequence_prefix = None
            scene.render.filepath = str(output_path)
        else:
            # Fallback for Blender builds where video container output is unavailable.
            self.is_png_fallback = True
            self.requested_video_path = output_path
            self.png_sequence_prefix = output_path.with_suffix("")
            scene.render.image_settings.file_format = "PNG"
            scene.render.filepath = str(self.png_sequence_prefix)
            print(
                "FFMPEG output is unavailable in this Blender build. "
                "Falling back to PNG sequence output."
            )

        print(f"Resolution set to {self.settings.resolution_y}p")

    def _configure_video_output(self, scene) -> bool:
        try:
            scene.render.image_settings.file_format = "FFMPEG"
            scene.render.ffmpeg.format = "MPEG4"
            scene.render.ffmpeg.codec = "H264"
            scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        except (TypeError, ValueError):
            return False
        return True

    def apply_eevee_enhancements(self) -> None:
        scene = bpy.context.scene
        if scene.render.engine != "BLENDER_EEVEE":
            return

        try:
            scene.eevee.use_gtao = True
            scene.eevee.use_bloom = True
            scene.eevee.use_ssr = True
            if hasattr(scene.eevee, "use_shadows"):
                scene.eevee.use_shadows = False
        except Exception:
            # Blender API flags can vary between versions.
            pass
