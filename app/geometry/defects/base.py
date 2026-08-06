from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    # Imported lazily: TrackSection pulls in bpy, and defect *metadata* must be
    # readable outside Blender (validation, annotation tooling). The annotations
    # below are strings at runtime thanks to `from __future__ import annotations`.
    from app.geometry.track_section import TrackSection


class Defect(ABC):
    """Abstract base for all track defect types.

    A defect has two separable halves:

      *metadata* — ``NAME``, ``variants()``, ``span_groups()``, ``span_sections()``
        and ``displacement_m()``. Pure data, importable without Blender.
      *behaviour* — ``apply()``, which mutates Blender objects.

    The metadata half is deliberately uniform across every defect type so that
    callers (constraint checks, annotation extents) can interrogate a defect
    without knowing which one it is. Adding a new defect type therefore requires
    no change to those callers.
    """

    NAME: str

    @classmethod
    @abstractmethod
    def variants(cls) -> List:
        """Return all fixed variants for this defect type."""

    @classmethod
    @abstractmethod
    def apply(cls, section: "TrackSection", params: dict) -> None:
        """Apply this defect to *section* using the given *params*."""

    @classmethod
    def span_groups(cls) -> List[List]:
        """Return variants grouped as ordered span sequences.

        Default: each variant is its own single-section span.
        Multi-section defects (e.g. lateral displacement) override this to
        return per-span lists ordered position 0 → N-1; DefectSelector queues
        positions 1..N-1 automatically when the span-start is chosen.
        """
        return [[v] for v in cls.variants()]

    # ── Uniform metadata ──────────────────────────────────────────────────────

    @classmethod
    def span_sections(cls, params: dict) -> int:
        """Number of consecutive sections this defect occupies.

        Multiplied by ``TrackGeometryConfig.section_pitch`` this gives the
        defect's physical length along the track — which is what determines
        whether it fits in a camera frame.
        """
        return int(params.get("span_length", 1))

    @classmethod
    def displacement_m(cls, params: dict) -> float:
        """Characteristic displacement magnitude in metres.

        Zero for defects that do not translate geometry (a rotated sleeper or a
        removed fastener changes the scene without displacing anything by a
        measurable offset). Used to reason about whether a defect is large
        enough to be visible at a given camera distance and resolution.
        """
        return float(params.get("displacement_m", 0.0))
