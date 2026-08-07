"""What a run reports about itself, as data.

One vocabulary, two audiences. A person watching a headless VM wants a short,
readable line; a UI wants the same facts as fields. Both read the *same* events,
so the console and the machine stream can never describe different runs.

Nothing here imports ``bpy`` or ``tqdm`` — this is the shape, not the rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Phase(StrEnum):
    """The stages of a run, in the order they happen.

    Phases exist because frames are a small part of the work. The first run of
    any new geometry builds hundreds of cached section prototypes before a
    single frame renders, and a progress bar that only counts frames sits at
    zero throughout, looking hung.
    """

    CACHE = "cache"       # building or loading section prototypes
    TRACK = "track"       # instantiating sections along the track
    SCENE = "scene"       # world, lighting, camera
    RENDER = "render"     # rendering frames
    ENCODE = "encode"     # assembling frames into video


class EventKind(StrEnum):
    PHASE_START = "phase_start"
    PROGRESS = "progress"
    PHASE_END = "phase_end"
    DONE = "done"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class ProgressEvent:
    """One thing that happened, reportable to any audience."""

    kind: EventKind
    phase: Phase | None = None
    done: int = 0
    total: int | None = None
    message: str = ""
    detail: dict = field(default_factory=dict)

    @property
    def fraction(self) -> float | None:
        """Completion of this phase in 0..1, or None when the total is unknown."""
        if not self.total:
            return None
        return min(1.0, self.done / self.total)

    def as_dict(self) -> dict:
        """Plain data, ready to serialise."""
        payload = {
            "event": str(self.kind),
            "phase": str(self.phase) if self.phase else None,
            "done": self.done,
            "total": self.total,
            "message": self.message,
        }
        if self.fraction is not None:
            payload["fraction"] = round(self.fraction, 4)
        if self.detail:
            payload["detail"] = self.detail
        return payload
