from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.geometry.track_section import TrackSection


class Defect(ABC):
    """Abstract base for all track defect types."""

    NAME: str

    @classmethod
    @abstractmethod
    def variants(cls) -> List:
        """Return all fixed variants for this defect type."""

    @classmethod
    @abstractmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
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
