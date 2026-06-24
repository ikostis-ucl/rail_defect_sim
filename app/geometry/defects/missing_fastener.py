from __future__ import annotations

from typing import List

import bpy

from app.geometry.defects.base import Defect
from app.geometry.defects.variant import DefectVariant
from app.geometry.track_section import TrackSection


class MissingFastenerPairDefect(Defect):
    """One of the four fastener pairs is missing from the section."""

    NAME = "missing_fastener_pair"
    PAIR_VARIANTS: List[int] = [0, 1, 2, 3]

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        return [
            DefectVariant(cls.NAME, {"pair_index": i}, cls)
            for i in cls.PAIR_VARIANTS
        ]

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        pair_index = int(params.get("pair_index", 0))
        start_idx = pair_index * 2
        for idx in sorted((start_idx, start_idx + 1), reverse=True):
            if 0 <= idx < len(section.fasteners):
                bpy.data.objects.remove(section.fasteners[idx], do_unlink=True)
                section.fasteners.pop(idx)
