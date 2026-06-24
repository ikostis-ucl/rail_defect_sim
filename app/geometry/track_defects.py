"""
Railway track defect implementations and probabilistic selector.

Defects inherit from the abstract Defect base class. Each subclass declares
its fixed variants and apply() logic. DefectSelector probabilistically picks
which cached variant to use per track section.
"""

from __future__ import annotations

import json
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import bpy

from app.geometry.track_section import TrackSection
from app.geometry.track_section_cache import SectionCacheBase


# ---------------------------------------------------------------------------
# DefectVariant — pure data carrier for one cached defect configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefectVariant:
    """Serializable descriptor for one cached defect variant."""

    defect_name: str
    defect_params: dict[str, float | int]
    defect_class: type = field(hash=False, compare=False)

    @property
    def identifier(self) -> str:
        return f"{self.defect_name}:{json.dumps(self.defect_params, sort_keys=True)}"

    def apply(self, section: TrackSection) -> None:
        self.defect_class.apply(section, self.defect_params)


# ---------------------------------------------------------------------------
# Defect base class
# ---------------------------------------------------------------------------


class Defect(ABC):
    """Abstract base for all track defect types."""

    NAME: str

    @classmethod
    @abstractmethod
    def variants(cls) -> List[DefectVariant]:
        """Return all fixed variants for this defect type."""

    @classmethod
    @abstractmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        """Apply this defect to *section* using the given *params*."""


# ---------------------------------------------------------------------------
# Concrete defect implementations
# ---------------------------------------------------------------------------


class SkewedBallastDefect(Defect):
    """Sleeper/ballast rotated by a fixed angle out of perpendicular alignment."""

    NAME = "skewed_ballast"
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
        for piece in (section.left_ballast, section.middle_ballast, section.right_ballast):
            if piece is not None:
                piece.rotation_euler[2] += angle_rad


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


# ---------------------------------------------------------------------------
# Registry of all known defect types
# ---------------------------------------------------------------------------


ALL_DEFECTS: List[type[Defect]] = [
    SkewedBallastDefect,
    MissingFastenerPairDefect,
]


# ---------------------------------------------------------------------------
# Defect section cache
# ---------------------------------------------------------------------------


class DefectiveSectionCache(SectionCacheBase):
    """Loads and stores reusable defective track section prototypes."""

    CACHE_VERSION = 4

    def __init__(self, cache_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        super().__init__(
            cache_dir or project_root / "assets" / "track_section_cache" / "defective"
        )

    def get_or_create_defective_collection(
        self,
        section: TrackSection,
        variant: DefectVariant,
    ):
        """Return a cached defective section collection for *variant*."""
        payload = {
            "cache_version": self.CACHE_VERSION,
            "defect_name": variant.defect_name,
            **section.geometry_payload(),
            **variant.defect_params,
        }
        cache_key = self._make_cache_key(payload)
        collection_name = f"DefectiveSection_{variant.defect_name}_{cache_key}"
        cache_path = self.cache_dir / f"{collection_name}.blend"

        existing = bpy.data.collections.get(collection_name)
        if existing is not None:
            print(f"Defective section cache hit (memory): {collection_name}")
            return existing

        if cache_path.exists():
            loaded = self._load_collection(cache_path, collection_name)
            if loaded is not None:
                print(f"Defective section cache hit (disk): {cache_path.name}")
                return loaded

        print(f"Defective section cache miss: building {collection_name}")
        collection = self._build_collection(collection_name, section, variant)
        self._write_collection(cache_path, collection)
        print(f"Defective section cache stored: {cache_path}")
        return collection

    def _build_collection(
        self,
        collection_name: str,
        section: TrackSection,
        variant: DefectVariant,
    ):
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)
        variant.apply(section)

        collection["cache_version"] = self.CACHE_VERSION
        collection["defect_name"] = variant.defect_name
        collection["defect_params"] = json.dumps(variant.defect_params, sort_keys=True)
        collection["track_section_geometry"] = json.dumps(
            section.geometry_payload(), sort_keys=True
        )
        return collection


# ---------------------------------------------------------------------------
# Defect selector
# ---------------------------------------------------------------------------


class DefectSelector:
    """
    Probabilistic dispatcher that decides whether a track section is defective
    and, if so, which pre-cached defect variant to use.

    * ``DEFECT_PROBABILITY`` (10 %) of sections receive a defect.
    * All registered variants are equally likely within that 10 %.
    """

    DEFECT_PROBABILITY: float = 0.10

    def __init__(self, seed: Optional[int] = None) -> None:
        self._variants: List[DefectVariant] = []
        self._rng: random.Random = random.Random(seed)

    def register(self, variant: DefectVariant) -> None:
        self._variants.append(variant)

    def all_variants(self) -> List[DefectVariant]:
        return list(self._variants)

    def select_variant(self) -> Optional[DefectVariant]:
        """Return a defect variant for the next section, or None for a healthy one."""
        if not self._variants:
            return None
        if self._rng.random() < self.DEFECT_PROBABILITY:
            return self._rng.choice(self._variants)
        return None

    @classmethod
    def default(cls, seed: Optional[int] = None) -> "DefectSelector":
        """Create a DefectSelector pre-populated with all known defect variants."""
        selector = cls(seed=seed)
        for defect_class in ALL_DEFECTS:
            for variant in defect_class.variants():
                selector.register(variant)
        return selector
