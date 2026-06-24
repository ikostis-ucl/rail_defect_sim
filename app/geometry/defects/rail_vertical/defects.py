from app.geometry.defects.rail_vertical.base import RailVerticalDisplacementDefect


class LeftRailVerticalBumpDefect(RailVerticalDisplacementDefect):
    """Left rail bumped upward (+Z) over the span; sleeper stays put."""

    NAME = "left_rail_vertical_bump"
    BENDS = [("left", +1)]


class RightRailVerticalBumpDefect(RailVerticalDisplacementDefect):
    """Right rail bumped upward (+Z) over the span; sleeper stays put."""

    NAME = "right_rail_vertical_bump"
    BENDS = [("right", +1)]


class BothRailsVerticalBumpDefect(RailVerticalDisplacementDefect):
    """Both rails bumped upward together (+Z, shared height); sleepers stay put."""

    NAME = "both_rails_vertical_bump"
    BENDS = [("left", +1), ("right", +1)]
