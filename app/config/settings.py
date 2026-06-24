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

    # Camera placement and orientation. Defaults reproduce the original
    # bird's-eye view (2.45 m above the track centre, looking straight down).
    camera_height: float = 2.45            # Z position in metres
    camera_lateral_offset: float = 0.0     # X position in metres (+ = right of track)
    camera_tilt_deg: float = 0.0           # pitch about X: 0 = straight down, 90 = forward
    camera_yaw_deg: float = 0.0            # pan about vertical axis (turn left/right)
    camera_roll_deg: float = 0.0           # bank about the view axis
    camera_lens: float = 35.0              # focal length in mm (lower = wider FOV)

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

