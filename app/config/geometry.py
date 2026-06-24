"""
TrackGeometryConfig — single source of truth for all track geometry dimensions.

All values are in metres (1 Blender unit = 1 m).
Load from a YAML file with TrackGeometryConfig.from_yaml(path).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrackGeometryConfig:
    """
    Frozen dataclass holding every geometric parameter for one track section.

    section_pitch (the centre-to-centre spacing between consecutive sleepers)
    is a *derived* quantity:

        section_pitch = sleeper_length / sleeper_pitch_ratio

    Changing sleeper_length or sleeper_pitch_ratio automatically adjusts the
    pitch — the two values cannot drift apart.
    """

    # ── Rail ─────────────────────────────────────────────────────────────────
    rail_spacing: float = 1.435   # centre-to-centre, UIC standard gauge
    rail_height: float = 0.16
    rail_width: float = 0.06
    rail_lift: float = 0.0        # extra clearance above top-of-sleeper
    # Rotation of both rails around the vertical (Z) axis, in degrees.
    # 0 = rails are parallel to the track axis (normal).
    # Non-zero values tilt the rails in the horizontal plane, e.g.:
    #   angle=0  →  || | ||   (normal)
    #   angle=5  →  \\ | \\   (both rails rotated 5° clockwise)
    rail_angle: float = 0.0

    # ── Sleeper (the wooden plank under the rails) ────────────────────────────
    sleeper_length: float = 0.108   # body length along the track axis (Y)
    sleeper_height: float = 0.12    # body height (Z)
    # Fraction of centre-to-centre pitch occupied by the sleeper body.
    # section_pitch = sleeper_length / sleeper_pitch_ratio
    # Default: 0.108 / 0.60 = 0.18 m  (matches prior hardcoded section_spacing)
    sleeper_pitch_ratio: float = 0.60

    # ── Fasteners (screws securing rails to sleepers) ─────────────────────────
    screw_radius: float = 0.015
    screw_length: float = 0.05

    # ── Derived ──────────────────────────────────────────────────────────────

    @property
    def section_pitch(self) -> float:
        """Centre-to-centre distance between consecutive sleeper positions (m)."""
        return self.sleeper_length / self.sleeper_pitch_ratio

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict of all fields (suitable for cache key hashing)."""
        return dataclasses.asdict(self)

    # ── Construction ──────────────────────────────────────────────────────────

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TrackGeometryConfig":
        """Load geometry config from a YAML file.

        Only keys present in the file override defaults; unknown keys are
        silently ignored so that partial override files are valid.
        """
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyyaml is required to load geometry config files. "
                "Install it with: pip install pyyaml"
            ) from exc

        with open(path, "r", encoding="utf-8") as fh:
            raw: dict = yaml.safe_load(fh) or {}

        known = {f.name for f in dataclasses.fields(cls)}
        overrides = {k: v for k, v in raw.items() if k in known}
        return dataclasses.replace(cls(), **overrides)
