from __future__ import annotations

import math
from typing import List

from app.geometry.defects.base import Defect
from app.geometry.defects.variant import DefectVariant
from app.geometry.track_section import TrackSection


class RailDisplacementDefect(Defect):
    """
    Base for sine-arch lateral rail-bend defects.

    Each rail named in ``BENDS`` is sheared along a half-sine arch — zero at both
    ends of the span, peaking at ``displacement_m`` in the centre — so the bend is
    continuous across section boundaries. The merged monoblock sleeper stays fixed
    (a concrete sleeper does not follow individual rail movement); only the rail
    mesh and the outer fastener pair are displaced.

    Subclasses set ``NAME`` and ``BENDS``: a list of ``(side, sign)`` tuples where
    ``side`` is ``"left"``/``"right"`` and ``sign`` is ``+1`` for +X or ``-1`` for -X.
    One tuple bends a single rail; two tuples bend both rails at once.
    """

    DISPLACEMENT_VARIANTS: List[float] = [0.03, 0.06, 0.10]
    SPAN_LENGTHS: List[int] = [5, 7]
    BENDS: List[tuple] = []

    # side → (rail attr, (entry-fastener idx, exit-fastener idx))
    _SIDE_OBJECTS = {
        "left":  ("left_rail",  (0, 1)),
        "right": ("right_rail", (6, 7)),
    }

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        return [
            DefectVariant(
                cls.NAME,
                {"displacement_m": d, "span_length": s, "position": p},
                cls,
            )
            for d in cls.DISPLACEMENT_VARIANTS
            for s in cls.SPAN_LENGTHS
            for p in range(s)
        ]

    @classmethod
    def span_groups(cls) -> List[List[DefectVariant]]:
        return [
            [
                DefectVariant(
                    cls.NAME,
                    {"displacement_m": d, "span_length": s, "position": p},
                    cls,
                )
                for p in range(s)
            ]
            for d in cls.DISPLACEMENT_VARIANTS
            for s in cls.SPAN_LENGTHS
        ]

    @classmethod
    def apply(cls, section: TrackSection, params: dict) -> None:
        displacement_m = float(params.get("displacement_m", 0.03))
        span_length = int(params.get("span_length", 5))
        position = int(params.get("position", 0))
        for side, sign in cls.BENDS:
            cls._displace_rail(
                section,
                side=side,
                sign=sign,
                displacement_m=displacement_m,
                span_length=span_length,
                position=position,
            )

    @classmethod
    def _displace_rail(
        cls, section: TrackSection, *, side: str, sign: int,
        displacement_m: float, span_length: int, position: int,
    ) -> None:
        cfg = section.config

        # Sine arch: section i covers [i/N, (i+1)/N]; adjacent sections share
        # the same offset at their shared boundary → no discontinuity at joints.
        t_entry = position / span_length
        t_exit  = (position + 1) / span_length
        x_entry = sign * displacement_m * math.sin(math.pi * t_entry)
        x_exit  = sign * displacement_m * math.sin(math.pi * t_exit)

        rail_attr, (entry_idx, exit_idx) = cls._SIDE_OBJECTS[side]
        rail = getattr(section, rail_attr, None)

        if rail is not None:
            cls._bend_mesh(rail, x_entry, x_exit, axis="x")
        # The merged monoblock sleeper stays fixed — a rigid concrete sleeper
        # does not follow individual rail lateral movement.

        # Outer fasteners: interpolate by their y-position within the section
        pair_offset_y = max(cfg.sleeper_depth * 0.24, 0.02)
        t_near = 0.5 - pair_offset_y / cfg.section_pitch
        t_far  = 0.5 + pair_offset_y / cfg.section_pitch
        for idx, t_local in ((entry_idx, t_near), (exit_idx, t_far)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.x += (
                    x_entry * (1.0 - t_local) + x_exit * t_local
                )

    @classmethod
    def _bend_mesh(cls, obj, entry: float, exit: float, axis: str = "x") -> None:
        """Linearly shear obj's vertices along *axis* as a function of local Y.

        y=-0.5 (entry face) → *entry* world offset; y=+0.5 (exit face) → *exit*.
        Intermediate vertices are interpolated, producing a continuous bend.
        Assumes the object has no rotation (scale-only transform), so world axis
        i maps to local axis i.
        """
        i = {"x": 0, "y": 1, "z": 2}[axis]
        scale = obj.scale[i]
        for v in obj.data.vertices:
            t = v.co.y + 0.5
            delta_world = entry * (1.0 - t) + exit * t
            v.co[i] += delta_world / scale
        obj.data.update()
