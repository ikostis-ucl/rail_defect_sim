from app.geometry.defects.rail_displacement.base import RailDisplacementDefect


class RightRailLateralDisplacementDefect(RailDisplacementDefect):
    """Right rail bent outward (+X), widening the gauge on the right."""

    NAME = "right_rail_lateral_displacement"
    BENDS = [("right", +1)]


class LeftRailLateralDisplacementDefect(RailDisplacementDefect):
    """Left rail bent outward (-X), widening the gauge on the left."""

    NAME = "left_rail_lateral_displacement"
    BENDS = [("left", -1)]


class LeftRailInwardDisplacementDefect(RailDisplacementDefect):
    """Left rail bent inward (+X), toward the track centre."""

    NAME = "left_rail_inward_displacement"
    BENDS = [("left", +1)]


class RightRailInwardDisplacementDefect(RailDisplacementDefect):
    """Right rail bent inward (-X), toward the track centre."""

    NAME = "right_rail_inward_displacement"
    BENDS = [("right", -1)]


class BothRailsGaugeWideningDefect(RailDisplacementDefect):
    """Both rails bent outward: gauge widens (left −X, right +X)."""

    NAME = "both_rails_gauge_widening"
    BENDS = [("left", -1), ("right", +1)]


class BothRailsGaugeNarrowingDefect(RailDisplacementDefect):
    """Both rails bent inward: gauge narrows (left +X, right −X)."""

    NAME = "both_rails_gauge_narrowing"
    BENDS = [("left", +1), ("right", -1)]


class BothRailsShiftLeftDefect(RailDisplacementDefect):
    """Both rails shifted toward −X: whole track laterally shifts left."""

    NAME = "both_rails_shift_left"
    BENDS = [("left", -1), ("right", -1)]


class BothRailsShiftRightDefect(RailDisplacementDefect):
    """Both rails shifted toward +X: whole track laterally shifts right."""

    NAME = "both_rails_shift_right"
    BENDS = [("left", +1), ("right", +1)]
