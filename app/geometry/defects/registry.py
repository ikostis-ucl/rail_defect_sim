from __future__ import annotations

from typing import List

from app.geometry.defects.base import Defect
from app.geometry.defects.skewed_sleeper import SkewedSleeperDefect
from app.geometry.defects.missing_fastener import MissingFastenerPairDefect
from app.geometry.defects.rail_displacement import (
    RightRailLateralDisplacementDefect,
    LeftRailLateralDisplacementDefect,
    LeftRailInwardDisplacementDefect,
    RightRailInwardDisplacementDefect,
    BothRailsGaugeWideningDefect,
    BothRailsGaugeNarrowingDefect,
    BothRailsShiftLeftDefect,
    BothRailsShiftRightDefect,
)
from app.geometry.defects.rail_vertical import (
    LeftRailVerticalBumpDefect,
    RightRailVerticalBumpDefect,
    BothRailsVerticalBumpDefect,
)

ALL_DEFECTS: List[type[Defect]] = [
    SkewedSleeperDefect,
    MissingFastenerPairDefect,
    # Single-rail bends
    RightRailLateralDisplacementDefect,
    LeftRailLateralDisplacementDefect,
    LeftRailInwardDisplacementDefect,
    RightRailInwardDisplacementDefect,
    # Both-rail bends (every direction combination)
    BothRailsGaugeWideningDefect,
    BothRailsGaugeNarrowingDefect,
    BothRailsShiftLeftDefect,
    BothRailsShiftRightDefect,
    # Vertical rail bumps (rail lifts off its seat)
    LeftRailVerticalBumpDefect,
    RightRailVerticalBumpDefect,
    BothRailsVerticalBumpDefect,
]
