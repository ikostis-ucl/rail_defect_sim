from dataclasses import dataclass


@dataclass(frozen=True)
class TrackSectionLayout:
    """Computed X-axis positions for a single cross-section assembly."""

    left_rail_x: float
    right_rail_x: float
    sleeper_x: float
    sleeper_width: float
