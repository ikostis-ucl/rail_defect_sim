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

    @classmethod
    def span_groups(cls) -> List[List[DefectVariant]]:
        """
        Return variants grouped into ordered position sequences (spans).

        Default: each variant is its own single-section span.
        Multi-section defects override this to return per-span lists ordered
        position 0 → N-1; DefectSelector queues positions 1..N-1 automatically.
        """
        return [[v] for v in cls.variants()]

    @classmethod
    def _bend_mesh_x(cls, obj, x_entry: float, x_exit: float) -> None:
        """
        Linearly shear *obj*'s vertices in X along its local Y axis.

        Vertices at local y = -0.5 (entry face) shift by *x_entry* in world X;
        vertices at local y = +0.5 (exit face) shift by *x_exit*. Intermediate
        vertices are interpolated. Assumes obj has no rotation (scale-only transform).
        """
        scale_x = obj.scale.x
        for v in obj.data.vertices:
            t = v.co.y + 0.5          # 0.0 at entry face, 1.0 at exit face
            dx_world = x_entry * (1.0 - t) + x_exit * t
            v.co.x += dx_world / scale_x
        obj.data.update()


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


class RightRailLateralDisplacementDefect(Defect):
    """
    Right rail displaced laterally outward over a span of consecutive sections.

    The offset profile follows a half-sine arch: zero at both ends of the span,
    peaking at ``displacement_m`` in the centre.  The outer ballast bed and
    outer-right fastener pair (indices 6–7) follow the rail so each section
    looks coherent in isolation.
    """

    NAME = "right_rail_lateral_displacement"
    # Peak displacement in metres: mild / moderate / severe
    DISPLACEMENT_VARIANTS: List[float] = [0.03, 0.06, 0.10]
    # Number of consecutive sections the defect spans
    SPAN_LENGTHS: List[int] = [5, 7]

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        """All (displacement_m, span_length, position) combinations."""
        result = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                for position in range(span_length):
                    result.append(DefectVariant(
                        cls.NAME,
                        {
                            "displacement_m": displacement_m,
                            "span_length": span_length,
                            "position": position,
                        },
                        cls,
                    ))
        return result

    @classmethod
    def span_groups(cls) -> List[List[DefectVariant]]:
        """Variants grouped into ordered position sequences, one group per span."""
        groups = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                groups.append([
                    DefectVariant(
                        cls.NAME,
                        {
                            "displacement_m": displacement_m,
                            "span_length": span_length,
                            "position": i,
                        },
                        cls,
                    )
                    for i in range(span_length)
                ])
        return groups

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        displacement_m = float(params.get("displacement_m", 0.03))
        span_length = int(params.get("span_length", 5))
        position = int(params.get("position", 0))

        # Continuous sine along the whole span: t=0 at span start, t=1 at span end.
        # Each section covers [position/N, (position+1)/N], so adjacent sections
        # share exactly the same offset at their shared boundary → zero discontinuity.
        t_entry = position / span_length
        t_exit = (position + 1) / span_length
        x_entry = displacement_m * math.sin(math.pi * t_entry)
        x_exit = displacement_m * math.sin(math.pi * t_exit)

        # Shear the right rail vertices: entry face → x_entry, exit face → x_exit
        if section.right_rail is not None:
            cls._bend_mesh_x(section.right_rail, x_entry, x_exit)

        # Translate right ballast rigidly (sleepers stay straight, not bent)
        if section.right_ballast is not None:
            section.right_ballast.location.x += (x_entry + x_exit) / 2

        # Outer-right fasteners (indices 6 & 7) are at ±pair_offset_y from section
        # centre; interpolate their x-offset from the actual y-position within the section.
        pair_offset_y = max((section.length * section.ballast_length_ratio) * 0.24, 0.02)
        t6 = 0.5 - pair_offset_y / section.rail_length  # entry-side fastener
        t7 = 0.5 + pair_offset_y / section.rail_length  # exit-side fastener
        for idx, t_local in ((6, t6), (7, t7)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.x += x_entry * (1.0 - t_local) + x_exit * t_local


class LeftRailLateralDisplacementDefect(Defect):
    """
    Left rail displaced laterally outward (negative X) over a span of consecutive sections.

    Symmetric counterpart of RightRailLateralDisplacementDefect. The half-sine
    arch profile and vertex-shear technique are identical; only the sign of the
    displacement and the affected objects differ.
    """

    NAME = "left_rail_lateral_displacement"
    DISPLACEMENT_VARIANTS: List[float] = [0.03, 0.06, 0.10]
    SPAN_LENGTHS: List[int] = [5, 7]

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        result = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                for position in range(span_length):
                    result.append(DefectVariant(
                        cls.NAME,
                        {
                            "displacement_m": displacement_m,
                            "span_length": span_length,
                            "position": position,
                        },
                        cls,
                    ))
        return result

    @classmethod
    def span_groups(cls) -> List[List[DefectVariant]]:
        groups = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                groups.append([
                    DefectVariant(
                        cls.NAME,
                        {
                            "displacement_m": displacement_m,
                            "span_length": span_length,
                            "position": i,
                        },
                        cls,
                    )
                    for i in range(span_length)
                ])
        return groups

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        displacement_m = float(params.get("displacement_m", 0.03))
        span_length = int(params.get("span_length", 5))
        position = int(params.get("position", 0))

        t_entry = position / span_length
        t_exit = (position + 1) / span_length
        # Negative: left rail moves in the -X direction
        x_entry = -displacement_m * math.sin(math.pi * t_entry)
        x_exit = -displacement_m * math.sin(math.pi * t_exit)

        if section.left_rail is not None:
            cls._bend_mesh_x(section.left_rail, x_entry, x_exit)

        if section.left_ballast is not None:
            section.left_ballast.location.x += (x_entry + x_exit) / 2

        # Outer-left fastener pair: indices 0 (entry-side) and 1 (exit-side)
        pair_offset_y = max((section.length * section.ballast_length_ratio) * 0.24, 0.02)
        t0 = 0.5 - pair_offset_y / section.rail_length
        t1 = 0.5 + pair_offset_y / section.rail_length
        for idx, t_local in ((0, t0), (1, t1)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.x += x_entry * (1.0 - t_local) + x_exit * t_local


class LeftRailInwardDisplacementDefect(Defect):
    """
    Left rail displaced laterally inward (positive X, toward track centre).

    Symmetric counterpart of LeftRailLateralDisplacementDefect: same sine-arch
    profile and vertex-shear technique, but the rail curves toward the centre
    rather than outward, narrowing the gauge.
    """

    NAME = "left_rail_inward_displacement"
    DISPLACEMENT_VARIANTS: List[float] = [0.03, 0.06, 0.10]
    SPAN_LENGTHS: List[int] = [5, 7]

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        result = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                for position in range(span_length):
                    result.append(DefectVariant(
                        cls.NAME,
                        {"displacement_m": displacement_m, "span_length": span_length, "position": position},
                        cls,
                    ))
        return result

    @classmethod
    def span_groups(cls) -> List[List[DefectVariant]]:
        groups = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                groups.append([
                    DefectVariant(
                        cls.NAME,
                        {"displacement_m": displacement_m, "span_length": span_length, "position": i},
                        cls,
                    )
                    for i in range(span_length)
                ])
        return groups

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        displacement_m = float(params.get("displacement_m", 0.03))
        span_length = int(params.get("span_length", 5))
        position = int(params.get("position", 0))

        t_entry = position / span_length
        t_exit = (position + 1) / span_length
        # Positive: left rail moves toward the centre (+X)
        x_entry = displacement_m * math.sin(math.pi * t_entry)
        x_exit = displacement_m * math.sin(math.pi * t_exit)

        if section.left_rail is not None:
            cls._bend_mesh_x(section.left_rail, x_entry, x_exit)

        if section.left_ballast is not None:
            section.left_ballast.location.x += (x_entry + x_exit) / 2

        pair_offset_y = max((section.length * section.ballast_length_ratio) * 0.24, 0.02)
        t0 = 0.5 - pair_offset_y / section.rail_length
        t1 = 0.5 + pair_offset_y / section.rail_length
        for idx, t_local in ((0, t0), (1, t1)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.x += x_entry * (1.0 - t_local) + x_exit * t_local


class RightRailInwardDisplacementDefect(Defect):
    """
    Right rail displaced laterally inward (negative X, toward track centre).

    Symmetric counterpart of RightRailLateralDisplacementDefect: same sine-arch
    profile and vertex-shear technique, but the rail curves toward the centre
    rather than outward, narrowing the gauge.
    """

    NAME = "right_rail_inward_displacement"
    DISPLACEMENT_VARIANTS: List[float] = [0.03, 0.06, 0.10]
    SPAN_LENGTHS: List[int] = [5, 7]

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        result = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                for position in range(span_length):
                    result.append(DefectVariant(
                        cls.NAME,
                        {"displacement_m": displacement_m, "span_length": span_length, "position": position},
                        cls,
                    ))
        return result

    @classmethod
    def span_groups(cls) -> List[List[DefectVariant]]:
        groups = []
        for displacement_m in cls.DISPLACEMENT_VARIANTS:
            for span_length in cls.SPAN_LENGTHS:
                groups.append([
                    DefectVariant(
                        cls.NAME,
                        {"displacement_m": displacement_m, "span_length": span_length, "position": i},
                        cls,
                    )
                    for i in range(span_length)
                ])
        return groups

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        displacement_m = float(params.get("displacement_m", 0.03))
        span_length = int(params.get("span_length", 5))
        position = int(params.get("position", 0))

        t_entry = position / span_length
        t_exit = (position + 1) / span_length
        # Negative: right rail moves toward the centre (-X)
        x_entry = -displacement_m * math.sin(math.pi * t_entry)
        x_exit = -displacement_m * math.sin(math.pi * t_exit)

        if section.right_rail is not None:
            cls._bend_mesh_x(section.right_rail, x_entry, x_exit)

        if section.right_ballast is not None:
            section.right_ballast.location.x += (x_entry + x_exit) / 2

        pair_offset_y = max((section.length * section.ballast_length_ratio) * 0.24, 0.02)
        t6 = 0.5 - pair_offset_y / section.rail_length
        t7 = 0.5 + pair_offset_y / section.rail_length
        for idx, t_local in ((6, t6), (7, t7)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.x += x_entry * (1.0 - t_local) + x_exit * t_local


# ---------------------------------------------------------------------------
# Registry of all known defect types
# ---------------------------------------------------------------------------


ALL_DEFECTS: List[type[Defect]] = [
    SkewedBallastDefect,
    MissingFastenerPairDefect,
    RightRailLateralDisplacementDefect,
    LeftRailLateralDisplacementDefect,
    LeftRailInwardDisplacementDefect,
    RightRailInwardDisplacementDefect,
]


# ---------------------------------------------------------------------------
# Defect section cache
# ---------------------------------------------------------------------------


class DefectiveSectionCache(SectionCacheBase):
    """Loads and stores reusable defective track section prototypes."""

    CACHE_VERSION = 8

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

    * ``DEFECT_PROBABILITY`` (10 %) of sections *start* a defect span.
    * All registered span-starts are equally likely within that 10 %.
    * For multi-section defects the follower positions are queued automatically
      so consecutive sections receive the correct part of the profile.
    """

    DEFECT_PROBABILITY: float = 0.10

    def __init__(self, seed: Optional[int] = None) -> None:
        self._variants: List[DefectVariant] = []
        # Maps span-start identifier → ordered list of follower variants
        self._span_followers: dict[str, List[DefectVariant]] = {}
        self._pending_queue: List[DefectVariant] = []
        self._rng: random.Random = random.Random(seed)

    def register(self, variant: DefectVariant) -> None:
        """Register a single-section variant."""
        self._variants.append(variant)

    def register_span(self, span_variants: List[DefectVariant]) -> None:
        """
        Register an ordered span sequence.

        Only position 0 enters the selectable pool; positions 1..N-1 are stored
        as followers and queued automatically when the span-start is chosen.
        """
        if not span_variants:
            return
        start = span_variants[0]
        self._variants.append(start)
        if len(span_variants) > 1:
            self._span_followers[start.identifier] = list(span_variants[1:])

    def all_variants(self) -> List[DefectVariant]:
        """Return every variant (span starts + followers) for pre-building caches."""
        result = list(self._variants)
        for followers in self._span_followers.values():
            result.extend(followers)
        return result

    def select_variant(self) -> Optional[DefectVariant]:
        """Return a defect variant for the next section, or None for a healthy one."""
        # Drain any queued span followers before rolling for a new defect
        if self._pending_queue:
            return self._pending_queue.pop(0)
        if not self._variants:
            return None
        if self._rng.random() < self.DEFECT_PROBABILITY:
            chosen = self._rng.choice(self._variants)
            if chosen.identifier in self._span_followers:
                self._pending_queue.extend(self._span_followers[chosen.identifier])
            return chosen
        return None

    @classmethod
    def default(cls, seed: Optional[int] = None) -> "DefectSelector":
        """Create a DefectSelector pre-populated with all known defect variants."""
        selector = cls(seed=seed)
        for defect_class in ALL_DEFECTS:
            for span_group in defect_class.span_groups():
                selector.register_span(span_group)
        return selector
