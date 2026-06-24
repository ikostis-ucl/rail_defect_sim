from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.geometry.track_section import TrackSection


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
