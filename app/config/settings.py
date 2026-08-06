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
from app.config.geometry import TrackGeometryConfig
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
    geometry: TrackGeometryConfig = field(default_factory=TrackGeometryConfig)

    # ── Run-level values ──────────────────────────────────────────────────────
    output_filename: str = field(default_factory=_default_output_filename)
    track_length: int = 100000
    base_speed_units_per_frame: float = 2.5

    # Provenance only: which .yml `geometry` was loaded from, or None for
    # defaults. The geometry itself is resolved at parse time so that a complete
    # run can be validated before Blender is launched.
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
    def output_dir(self) -> Path:
        """Directory this run writes into. Pure — creates nothing."""
        project_root = Path(__file__).resolve().parents[2]
        return project_root / "data" / "output" / self.run_name

    @property
    def output_path(self) -> str:
        """Full path of the output file. Pure — creates nothing.

        Reading a config value must never touch the filesystem: pre-render
        validation inspects these settings, and it would otherwise litter
        ``data/output/`` with directories for runs that were rejected and never
        happened. Call ``ensure_output_dir()`` when actually about to write.
        """
        return str(self.output_dir / Path(self.output_filename).name)

    def ensure_output_dir(self) -> Path:
        """Create the output directory, and return it. The only side effect here."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    @property
    def total_travel_distance(self) -> float:
        """Metres the camera covers over the whole clip.

        Compared against ``track_length`` this says whether the camera runs off
        the end of the built track.
        """
        return self.base_speed_units_per_frame * self.total_frames
