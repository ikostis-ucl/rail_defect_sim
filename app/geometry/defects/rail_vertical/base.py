from __future__ import annotations

import math

from app.geometry.defects.rail_displacement.base import RailDisplacementDefect
from app.geometry.track_section import TrackSection


class RailVerticalDisplacementDefect(RailDisplacementDefect):
    """
    Base for sine-arch *vertical* rail-bump defects.

    Like the lateral displacement defects, the rail is bent along a half-sine
    arch over a span of consecutive sections (continuous across boundaries), but
    the offset is applied in +Z (upward) instead of sideways. The rail lifts off
    its seat: the sleeper stays put and only the rail mesh and its outer fastener
    pair rise. Reuses the inherited variant/span/apply machinery; only the
    per-rail displacement differs.

    Subclasses set ``NAME`` and ``BENDS`` (``sign`` is +1 for an upward bump).
    """

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
        z_entry = sign * displacement_m * math.sin(math.pi * t_entry)
        z_exit  = sign * displacement_m * math.sin(math.pi * t_exit)

        rail_attr, _sleeper_attr, (entry_idx, exit_idx) = cls._SIDE_OBJECTS[side]
        rail = getattr(section, rail_attr, None)

        # Bump the rail upward; the sleeper stays put (rail lifts off its seat).
        if rail is not None:
            cls._bend_mesh(rail, z_entry, z_exit, axis="z")

        # Outer fasteners follow the rail vertically (interpolated by y-position).
        pair_offset_y = max(cfg.sleeper_length * 0.24, 0.02)
        t_near = 0.5 - pair_offset_y / cfg.section_pitch
        t_far  = 0.5 + pair_offset_y / cfg.section_pitch
        for idx, t_local in ((entry_idx, t_near), (exit_idx, t_far)):
            if idx < len(section.fasteners):
                section.fasteners[idx].location.z += (
                    z_entry * (1.0 - t_local) + z_exit * t_local
                )
