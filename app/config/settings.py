"""
Top-level pipeline settings.

``PipelineSettings`` is a composition root: it owns one config object per
domain (render, camera, environment, appearance) plus the run-level values that
belong to no single domain. Each domain config is a frozen, ``bpy``-free
dataclass, so a complete run description can be built, inspected, and validated
without launching Blender.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.config.appearance import AppearanceConfig
from app.config.camera import CameraConfig
from app.config.environment import EnvironmentConfig
from app.config.render import RenderConfig


def _default_output_filename() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"rail_render_{timestamp}.mp4"


@dataclass(frozen=True)
class PipelineSettings:
    """Everything needed to describe one render, grouped by domain."""

    # ── Domain configs ────────────────────────────────────────────────────────
    render: RenderConfig = field(default_factory=RenderConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    appearance: AppearanceConfig = field(default_factory=AppearanceConfig)

    # ── Run-level values ──────────────────────────────────────────────────────
    output_filename: str = field(default_factory=_default_output_filename)
    track_length: int = 100000
    base_speed_units_per_frame: float = 2.5

    # Path to a geometry .yml; parsed separately by TrackGeometryConfig.from_yaml
    # because track dimensions are a distinct config channel from runtime settings.
    geometry_config_path: str | None = None

    force_defect: str | None = None   # if set, every section gets this defect
    seed: int = 42                    # RNG seed for defect placement

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def total_frames(self) -> int:
        return self.render.total_frames

    @property
    def run_name(self) -> str:
        filename = Path(self.output_filename).name
        stem = Path(filename).stem
        return stem or filename

    @property
    def output_path(self) -> str:
        project_root = Path(__file__).resolve().parents[2]
        run_dir = project_root / "data" / "output" / self.run_name
        run_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(self.output_filename).name
        return str(run_dir / filename)

    @property
    def total_travel_distance(self) -> float:
        """Metres the camera covers over the whole clip.

        Compared against ``track_length`` this says whether the camera runs off
        the end of the built track.
        """
        return self.base_speed_units_per_frame * self.total_frames
