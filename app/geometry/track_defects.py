"""
Railway track defect implementations and probabilistic selector.

Defects are organized as cached collections where each variant has a fixed
configuration (e.g., specific skew angle). The DefectSelector probabilistically
selects which cached defect variant to use for each track section.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import bpy

from app.geometry.track_section import TrackSection


# ---------------------------------------------------------------------------
# Concrete defect implementations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DefectVariant:
    """Serializable descriptor for one cached defect variant."""

    defect_name: str
    defect_params: dict[str, float | int]

    @property
    def identifier(self) -> str:
        return f"{self.defect_name}:{json.dumps(self.defect_params, sort_keys=True)}"


class SkewedBallastDefect:
    """
    Sleeper/ballast rotated by a fixed angle out of perpendicular alignment.

    Uses pre-defined angle variants (2° and 5° clockwise and counterclockwise)
    rather than random angles, enabling efficient caching.
    """

    # Fixed angle variants in degrees (positive = clockwise, negative = counter-clockwise)
    ANGLE_VARIANTS: List[float] = [
        -5.0,   # 5 degrees counter-clockwise
        -2.0,   # 2 degrees counter-clockwise
        2.0,    # 2 degrees clockwise
        5.0,    # 5 degrees clockwise
    ]

    @staticmethod
    def apply_angle(section: TrackSection, angle_deg: float) -> None:
        """
        Apply a fixed yaw skew to all three ballast pieces of *section*.

        Args:
            section: TrackSection whose ballast will be skewed.
            angle_deg: Rotation angle in degrees (positive = clockwise).
        """
        angle_rad = math.radians(angle_deg)

        # Rotate every ballast piece so the whole sleeper looks misaligned.
        for piece in (section.left_ballast, section.middle_ballast, section.right_ballast):
            if piece is not None:
                piece.rotation_euler[2] += angle_rad  # type: ignore

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        """Return all cached skewed-ballast variants."""
        return [
            DefectVariant("skewed_ballast", {"angle_deg": angle_deg})
            for angle_deg in cls.ANGLE_VARIANTS
        ]


class MissingFastenerPairDefect:
    """One of the four fastener pairs is missing from the section."""

    PAIR_VARIANTS: List[int] = [0, 1, 2, 3]

    @staticmethod
    def apply_pair(section: TrackSection, pair_index: int) -> None:
        """Remove one pair of fasteners based on pair creation order."""
        start_idx = pair_index * 2
        for idx in sorted((start_idx, start_idx + 1), reverse=True):
            if 0 <= idx < len(section.fasteners):
                fastener = section.fasteners[idx]
                bpy.data.objects.remove(fastener, do_unlink=True)
                section.fasteners.pop(idx)

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        """Return all cached missing-fastener-pair variants."""
        return [
            DefectVariant("missing_fastener_pair", {"pair_index": pair_index})
            for pair_index in cls.PAIR_VARIANTS
        ]


# ---------------------------------------------------------------------------
# Defect section cache
# ---------------------------------------------------------------------------


class DefectiveSectionCache:
    """
    Loads and stores reusable defective track section prototypes.
    
    Unlike the base TrackSectionCache, this caches pre-defected sections
    (e.g., skewed ballast at specific angles).
    """

    CACHE_VERSION = 4

    def __init__(self, cache_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.cache_dir = cache_dir or project_root / "assets" / "track_section_cache" / "defective"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_or_create_defective_collection(
        self,
        section: TrackSection,
        defect_name: str,
        defect_params: dict,
    ):
        """
        Return a cached defective section collection.

        Args:
            section: Prototype TrackSection (undefected) geometry template.
            defect_name: Name of the defect (e.g., "skewed_ballast").
            defect_params: Dict of parameters (e.g., {"angle_deg": 5.0}).

        Returns:
            A cached collection containing the defected geometry.
        """
        payload = {
            "cache_version": self.CACHE_VERSION,
            "defect_name": defect_name,
            **section.geometry_payload(),
            **defect_params,
        }
        cache_key = self._make_cache_key(payload)
        collection_name = f"DefectiveSection_{defect_name}_{cache_key}"
        cache_path = self.cache_dir / f"{collection_name}.blend"

        existing_collection = bpy.data.collections.get(collection_name)
        if existing_collection is not None:
            print(f"Defective section cache hit (memory): {collection_name}")
            return existing_collection

        if cache_path.exists():
            loaded_collection = self._load_collection(cache_path, collection_name)
            if loaded_collection is not None:
                print(f"Defective section cache hit (disk): {cache_path.name}")
                return loaded_collection

        print(f"Defective section cache miss: building {collection_name}")
        defective_collection = self._build_collection(
            collection_name, section, defect_name, defect_params
        )
        self._write_collection(cache_path, defective_collection)
        print(f"Defective section cache stored: {cache_path}")
        return defective_collection

    def _build_collection(self, collection_name: str, section: TrackSection, defect_name: str, defect_params: dict):
        """Build and apply defect to a collection."""
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)

        # Apply the defect
        if defect_name == "skewed_ballast":
            angle_deg = defect_params.get("angle_deg", 0.0)
            SkewedBallastDefect.apply_angle(section, angle_deg)
        elif defect_name == "missing_fastener_pair":
            pair_index = int(defect_params.get("pair_index", 0))
            MissingFastenerPairDefect.apply_pair(section, pair_index)
        else:
            raise ValueError(f"Unsupported defect type: {defect_name}")

        collection["cache_version"] = self.CACHE_VERSION
        collection["defect_name"] = defect_name
        collection["defect_params"] = json.dumps(defect_params, sort_keys=True)
        collection["track_section_geometry"] = json.dumps(section.geometry_payload(), sort_keys=True)
        return collection

    @staticmethod
    def _load_collection(cache_path: Path, collection_name: str):
        with bpy.data.libraries.load(str(cache_path), link=False) as (data_from, data_to):
            data_to.collections = [collection_name] if collection_name in data_from.collections else []

        if not data_to.collections:
            return None

        collection = data_to.collections[0]
        if collection is not None:
            collection.use_fake_user = True
        return collection

    @staticmethod
    def _write_collection(cache_path: Path, collection) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.data.libraries.write(str(cache_path), {collection})

    @staticmethod
    def _make_cache_key(payload: dict) -> str:
        # Convert all values to strings for consistent hashing
        hashable_payload = {k: str(v) for k, v in payload.items()}
        encoded_payload = json.dumps(hashable_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded_payload).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Defect selector
# ---------------------------------------------------------------------------


class DefectSelector:
    """
    Probabilistic dispatcher that decides whether a track section is defective
    and, if so, which pre-cached defect variant to use.

    Rules
    -----
    * ``DEFECT_PROBABILITY`` (10 %) of all sections receive a defect.
    * All registered defect variants are equally likely within that 10 %.
    * Defect variants are pre-cached, so rendering is efficient.

    Usage::

        selector = DefectSelector.default(seed=42)
        variant = selector.select_variant()   # None or DefectVariant
        if variant is not None:
            print(variant)
    """

    DEFECT_PROBABILITY: float = 0.10

    def __init__(self, seed: Optional[int] = None) -> None:
        self._variants: List[DefectVariant] = []
        self._rng: random.Random = random.Random(seed)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, variant: DefectVariant) -> None:
        """Register one defect variant for equal-probability selection."""
        self._variants.append(variant)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def all_variants(self) -> List[DefectVariant]:
        """Return all registered variants in registration order."""
        return list(self._variants)

    def select_variant(self) -> Optional[DefectVariant]:
        """
        Roll the dice for the next section.

        Returns:
            The chosen defect variant when a defect should be applied,
            or ``None`` for a normal (healthy) section.
        """
        if not self._variants:
            return None
        if self._rng.random() < self.DEFECT_PROBABILITY:
            return self._rng.choice(self._variants)
        return None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def default(cls, seed: Optional[int] = None) -> "DefectSelector":
        """
        Create a :class:`DefectSelector` pre-populated with all known defect variants.

        Args:
            seed: Optional integer seed for reproducible runs.
        """
        selector = cls(seed=seed)
        for variant in SkewedBallastDefect.variants():
            selector.register(variant)
        for variant in MissingFastenerPairDefect.variants():
            selector.register(variant)
        return selector


