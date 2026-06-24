from dataclasses import dataclass


@dataclass(frozen=True)
class TrackSectionLayout:
    """Computed X-axis positions for a single cross-section assembly."""

    left_sleeper_x: float
    left_rail_x: float
    middle_sleeper_x: float
    middle_sleeper_width: float
    right_rail_x: float
    right_sleeper_x: float
    side_sleeper_width: float
