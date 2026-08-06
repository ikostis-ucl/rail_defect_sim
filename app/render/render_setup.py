"""Render builder — applies a RenderConfig to the Blender scene.

The *builder* half of rendering. The *data* half is
``app.config.render.RenderConfig``.
"""

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

    @property
    def config(self):
        return self.settings.render

    def apply(self) -> None:
        scene = bpy.context.scene
        cfg = self.config

        print(
            f"Setting up render settings: {cfg.total_frames} frames at {cfg.fps} fps "
            f"({cfg.total_frames / cfg.fps} seconds)..."
        )

        scene.render.engine = cfg.engine
        scene.render.resolution_x = cfg.resolution_x
        scene.render.resolution_y = cfg.resolution_y
        scene.render.fps = cfg.fps
        scene.frame_start = cfg.start_frame
        scene.frame_end = cfg.total_frames

        # The render is about to write here, so this is where the directory is
        # created — not when the path is merely read.
        self.settings.ensure_output_dir()
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

        print(f"Resolution set to {cfg.resolution_y}p")

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
        if scene.render.engine != self.config.engine:
            return
        if not self.config.engine.startswith("BLENDER_EEVEE"):
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
