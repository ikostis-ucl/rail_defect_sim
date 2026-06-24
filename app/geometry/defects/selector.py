from __future__ import annotations

import random
from typing import List, Optional

from app.geometry.defects.registry import ALL_DEFECTS
from app.geometry.defects.variant import DefectVariant


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
