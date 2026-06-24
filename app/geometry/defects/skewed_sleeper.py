from __future__ import annotations

import math
from typing import List

from app.geometry.defects.base import Defect
from app.geometry.defects.variant import DefectVariant
from app.geometry.track_section import TrackSection


class SkewedSleeperDefect(Defect):
    """Sleeper rotated by a fixed angle out of perpendicular alignment."""

    NAME = "skewed_sleeper"
    ANGLE_VARIANTS: List[float] = [-5.0, -2.0, 2.0, 5.0]

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        return [
            DefectVariant(cls.NAME, {"angle_deg": angle}, cls)
            for angle in cls.ANGLE_VARIANTS
        ]

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        angle_rad = math.radians(params.get("angle_deg", 0.0))
        for piece in (section.left_sleeper, section.middle_sleeper, section.right_sleeper):
            if piece is not None:
                piece.rotation_euler[2] += angle_rad
