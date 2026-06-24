from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


def _default_output_filename() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"rail_render_{timestamp}.mp4"


@dataclass(frozen=True)
class PipelineSettings:
    """Runtime settings for the generation pipeline."""

    fps: int = 12
    duration_seconds: int = 10
    resolution_x: int = 960
    resolution_y: int = 540
    output_filename: str = field(default_factory=_default_output_filename)
    render_engine: str = "BLENDER_EEVEE"
    start_frame: int = 1
    track_length: int = 100000
    base_speed_units_per_frame: float = 2.5

    @property
    def total_frames(self) -> int:
        return int(self.duration_seconds * self.fps)

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

