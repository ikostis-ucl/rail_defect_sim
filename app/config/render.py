"""
Render configuration — output format, resolution, and frame range.

The *data* half of rendering. The *builder* half is ``app.render.RenderSetup``,
which applies this to the Blender scene. Nothing here imports ``bpy``.
"""

from __future__ import annotations

from dataclasses import dataclass

BLENDER_EEVEE = "BLENDER_EEVEE"


@dataclass(frozen=True)
class RenderConfig:
    """Resolution, frame rate, clip length, and engine."""

    resolution_x: int = 960
    resolution_y: int = 540
    fps: int = 12
    duration_seconds: int = 10
    engine: str = BLENDER_EEVEE
    start_frame: int = 1

    @property
    def total_frames(self) -> int:
        return int(self.duration_seconds * self.fps)

    @property
    def aspect_ratio(self) -> float:
        return self.resolution_x / self.resolution_y
