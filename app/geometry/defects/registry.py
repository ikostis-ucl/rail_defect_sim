from __future__ import annotations

from typing import List

from app.geometry.defects.base import Defect
from app.geometry.defects.sleepers import SkewedSleeperDefect
from app.geometry.defects.fasteners import MissingFastenerPairDefect
from app.geometry.defects.rails import (
    RightRailLateralDisplacementDefect,
    LeftRailLateralDisplacementDefect,
    LeftRailInwardDisplacementDefect,
    RightRailInwardDisplacementDefect,
    BothRailsGaugeWideningDefect,
    BothRailsGaugeNarrowingDefect,
    BothRailsShiftLeftDefect,
    BothRailsShiftRightDefect,
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
