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
    continuous across section boundaries. The matching sleeper is translated
    rigidly (sleepers stay straight) and the outer fastener pair follows the rail.

    Subclasses set ``NAME`` and ``BENDS``: a list of ``(side, sign)`` tuples where
    ``side`` is ``"left"``/``"right"`` and ``sign`` is ``+1`` for a bend toward +X
    or ``-1`` toward -X. One tuple bends a single rail; two tuples bend both rails
    at once (shared magnitude, independent direction).
    """

    # Peak displacement in metres: mild / moderate / severe
    DISPLACEMENT_VARIANTS: List[float] = [0.03, 0.06, 0.10]
    # Number of consecutive sections the defect spans
    SPAN_LENGTHS: List[int] = [5, 7]
    # (side, sign) tuples — overridden by subclasses
    BENDS: List[tuple] = []

    # side → (rail attr, sleeper attr, (entry-fastener idx, exit-fastener idx))
    _SIDE_OBJECTS = {
        "left": ("left_rail", "left_sleeper", (0, 1)),
        "right": ("right_rail", "right_sleeper", (6, 7)),
    }

    @classmethod
    def variants(cls) -> List[DefectVariant]:
        """All (displacement_m, span_length, position) combinations."""
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
        """Variants grouped into ordered position sequences, one group per span."""
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
    def _displace_rail(cls, section, *, side, sign, displacement_m, span_length, position) -> None:
        # Continuous sine along the whole span: section i covers [i/N, (i+1)/N],
        # so adjacent sections share the same offset at their boundary → no discontinuity.
        t_entry = position / span_length
        t_exit = (position + 1) / span_length
        x_entry = sign * displacement_m * math.sin(math.pi * t_entry)
        x_exit = sign * displacement_m * math.sin(math.pi * t_exit)

        rail_attr, sleeper_attr, (entry_idx, exit_idx) = cls._SIDE_OBJECTS[side]
        rail = getattr(section, rail_attr)
        sleeper = getattr(section, sleeper_attr)

        # Shear the rail vertices: entry face → x_entry, exit face → x_exit
        if rail is not None:
            cls._bend_mesh_x(rail, x_entry, x_exit)

        # Translate the sleeper rigidly so it stays straight (not bent)
        if sleeper is not None:
            sleeper.location.x += (x_entry + x_exit) / 2

        # Outer fasteners sit at ±pair_offset_y from section centre; interpolate
        # their x-offset from the actual y-position within the section.
        pair_offset_y = max((section.length * section.sleeper_length_ratio) * 0.24, 0.02)
        t_entry_fast = 0.5 - pair_offset_y / section.rail_length
        t_exit_fast = 0.5 + pair_offset_y / section.rail_length
        for idx, t_local in ((entry_idx, t_entry_fast), (exit_idx, t_exit_fast)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.x += x_entry * (1.0 - t_local) + x_exit * t_local

    @staticmethod
    def _bend_mesh_x(obj, x_entry: float, x_exit: float) -> None:
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


# --- Single-rail bends ------------------------------------------------------


class RightRailLateralDisplacementDefect(RailDisplacementDefect):
    """Right rail bent outward (+X), widening the gauge on the right."""

    NAME = "right_rail_lateral_displacement"
    BENDS = [("right", +1)]


class LeftRailLateralDisplacementDefect(RailDisplacementDefect):
    """Left rail bent outward (-X), widening the gauge on the left."""

    NAME = "left_rail_lateral_displacement"
    BENDS = [("left", -1)]


class LeftRailInwardDisplacementDefect(RailDisplacementDefect):
    """Left rail bent inward (+X), toward the track centre."""

    NAME = "left_rail_inward_displacement"
    BENDS = [("left", +1)]


class RightRailInwardDisplacementDefect(RailDisplacementDefect):
    """Right rail bent inward (-X), toward the track centre."""

    NAME = "right_rail_inward_displacement"
    BENDS = [("right", -1)]


# --- Both-rail bends (shared magnitude, every direction combination) --------


class BothRailsGaugeWideningDefect(RailDisplacementDefect):
    """Both rails bent outward: gauge widens (left -X, right +X)."""

    NAME = "both_rails_gauge_widening"
    BENDS = [("left", -1), ("right", +1)]


class BothRailsGaugeNarrowingDefect(RailDisplacementDefect):
    """Both rails bent inward: gauge narrows (left +X, right -X)."""

    NAME = "both_rails_gauge_narrowing"
    BENDS = [("left", +1), ("right", -1)]


class BothRailsShiftLeftDefect(RailDisplacementDefect):
    """Both rails bent toward -X: whole track shifts left (left outward, right inward)."""

    NAME = "both_rails_shift_left"
    BENDS = [("left", -1), ("right", -1)]


class BothRailsShiftRightDefect(RailDisplacementDefect):
    """Both rails bent toward +X: whole track shifts right (left inward, right outward)."""

    NAME = "both_rails_shift_right"
    BENDS = [("left", +1), ("right", +1)]
