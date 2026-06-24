from __future__ import annotations

import random
from typing import List, Optional

from app.geometry.defects.registry import ALL_DEFECTS
from app.geometry.defects.variant import DefectVariant


class DefectSelector:
    """
    Probabilistic dispatcher that decides whether a track section is defective
    and, if so, which pre-cached defect variant to use.

    * DEFECT_PROBABILITY (10%) of sections *start* a defect span.
    * All registered span-starts are equally likely within that 10%.
    * For multi-section defects (e.g. lateral displacement), follower positions
      are queued automatically so consecutive sections receive the correct part
      of the profile without re-rolling.

    Use DefectSelector.forced(name) to guarantee 100% coverage of one defect
    type — useful for smoke tests and defect-specific validation renders.
    """

    DEFECT_PROBABILITY: float = 0.10

    def __init__(self, seed: Optional[int] = None, *, probability: float | None = None) -> None:
        self._probability = probability if probability is not None else self.DEFECT_PROBABILITY
        self._variants: List[DefectVariant] = []
        self._span_followers: dict[str, List[DefectVariant]] = {}
        self._pending_queue: List[DefectVariant] = []
        self._rng: random.Random = random.Random(seed)

    def register(self, variant: DefectVariant) -> None:
        """Register a single-section variant (convenience wrapper for register_span)."""
        self.register_span([variant])

    def register_span(self, span_variants: List[DefectVariant]) -> None:
        """Register an ordered span sequence.

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
        if self._pending_queue:
            return self._pending_queue.pop(0)
        if not self._variants:
            return None
        if self._rng.random() < self._probability:
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

    @classmethod
    def forced(cls, defect_name: str, seed: Optional[int] = None) -> "DefectSelector":
        """Create a selector that always applies one specific defect (100% rate).

        Every section will be defective. Multi-section spans are queued
        automatically so the profile is continuous across the full track.
        Raises ValueError if defect_name is not in the registry.
        """
        defect_class = next((d for d in ALL_DEFECTS if d.NAME == defect_name), None)
        if defect_class is None:
            known = [d.NAME for d in ALL_DEFECTS]
            raise ValueError(
                f"Unknown defect {defect_name!r}. Known defects: {known}"
            )
        selector = cls(seed=seed, probability=1.0)
        for span_group in defect_class.span_groups():
            selector.register_span(span_group)
        return selector
