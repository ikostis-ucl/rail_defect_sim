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
