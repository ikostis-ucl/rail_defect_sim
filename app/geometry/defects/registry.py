from __future__ import annotations

from typing import List

from app.geometry.defects.base import Defect
from app.geometry.defects.skewed_sleeper import SkewedSleeperDefect
from app.geometry.defects.missing_fastener import MissingFastenerPairDefect

ALL_DEFECTS: List[type[Defect]] = [
    SkewedSleeperDefect,
    MissingFastenerPairDefect,
]
