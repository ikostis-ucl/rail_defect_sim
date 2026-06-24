# Canonical location: app/geometry/defects/
from app.geometry.defects.variant import DefectVariant
from app.geometry.defects.base import Defect
from app.geometry.defects.skewed_sleeper import SkewedSleeperDefect
from app.geometry.defects.missing_fastener import MissingFastenerPairDefect
from app.geometry.defects.registry import ALL_DEFECTS
from app.geometry.defects.selector import DefectSelector

__all__ = [
    "DefectVariant", "Defect",
    "SkewedSleeperDefect", "MissingFastenerPairDefect",
    "ALL_DEFECTS", "DefectSelector",
]
