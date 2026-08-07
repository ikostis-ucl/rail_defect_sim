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


#: Extra track built beyond what the camera covers, as a fraction. Without it
#: the clip ends exactly at the last section, which puts the end of the world in
#: the final frames.
TRACK_LENGTH_MARGIN = 0.10


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

    # Train speed in km/h — the unit a person actually thinks in, and the unit
    # the config file and the UI present. Everything internal derives from it;
    # nothing else stores a speed.
    #
    # This used to be metres per *frame*, which meant frame rate and physical
    # speed were the same knob: raising fps from 12 to 25 for a smoother clip
    # silently took the train from 108 km/h to 225 km/h. Frame rate now changes
    # only how finely the motion is sampled.
    speed_kmh: float = 80.0

    # Explicit track length in metres. ``None`` means derive it from how far the
    # camera actually travels, which is the normal case — a track shorter than
    # the clip renders empty space off the end, and a track far longer is build
    # time spent on geometry no frame ever sees. Set it only when a fixed-length
    # track is wanted, typically for dataset generation.
    track_length_override_m: float | None = None

    # Provenance only: which .yml `geometry` was loaded from, or None for
    # defaults. The geometry itself is resolved at parse time so that a complete
    # run can be validated before Blender is launched.
    geometry_config_path: str | None = None

    # Where to write machine-readable progress, one JSON object per line. None
    # means console only. A file rather than stdout because Blender writes
    # copiously to stdout and a consumer cannot filter a stream it does not own.
    progress_file: str | None = None

    # Suppress the human progress account. Only sensible when something else is
    # consuming progress_file; a headless run normally still wants a log.
    quiet: bool = False

    # Print the per-asset cache detail. Off by default: it is a few hundred
    # lines on a large track and useful only when debugging the cache.
    verbose: bool = False

    force_defect: str | None = None   # if set, every section gets this defect
    seed: int = 42                    # RNG seed for defect placement

    # Fraction of sections that *start* a defect. The single most important dial
    # for dataset generation: it sets the balance of healthy to faulty examples
    # in the training data. Note multi-section defects then occupy their
    # follower sections too, so the share of *defective* sections ends up
    # several times this value.
    defect_rate: float = 0.10

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
    def speed_ms(self) -> float:
        """Speed in metres per second — the machine's unit, not the user's."""
        return self.speed_kmh / 3.6

    @property
    def metres_per_frame(self) -> float:
        """Distance the camera advances between consecutive frames.

        Derived, never configured. Frame rate divides the same physical speed
        into more or fewer samples; it does not change how fast the train moves.
        """
        fps = self.render.fps
        return self.speed_ms / fps if fps > 0 else 0.0

    @property
    def total_travel_distance_m(self) -> float:
        """Metres the camera covers over the whole clip."""
        return self.speed_ms * self.render.duration_seconds

    @property
    def track_length_m(self) -> float:
        """Metres of track to build.

        Either the explicit override, or the distance travelled plus a margin so
        the camera never reaches the final section. Deriving it is what makes
        "the camera ran off the end of the track" impossible to configure rather
        than a mistake something has to catch afterwards.
        """
        if self.track_length_override_m is not None:
            return float(self.track_length_override_m)
        return self.total_travel_distance_m * (1.0 + TRACK_LENGTH_MARGIN)
