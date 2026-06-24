"""
Track geometry configuration — single source of truth for all dimensions.

All values are in metres (1 Blender unit = 1 m).
Load from a YAML file with TrackGeometryConfig.from_yaml(path).
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RailConfig:
    """
    Geometry for a single rail.

    Each rail is configured independently, allowing the left and right rails
    to have different angles (or, in future, different cross-sections).
    """

    width: float = 0.06
    height: float = 0.16
    lift: float = 0.0    # extra clearance above top-of-sleeper (m)
    # Rotation around the vertical (Z) axis, in degrees.
    # 0 = rail parallel to the track axis (normal).
    # Non-zero = rail tilted in the horizontal plane.
    angle: float = 0.0


@dataclass(frozen=True)
class TrackGeometryConfig:
    """
    Frozen dataclass holding every geometric parameter for one track section.

    section_pitch (the centre-to-centre spacing between consecutive sleepers)
    is a *derived* quantity:

        section_pitch = sleeper_length / sleeper_pitch_ratio

    Changing sleeper_length or sleeper_pitch_ratio automatically adjusts the
    pitch — the two values cannot drift apart.

    Each rail is configured independently via left_rail / right_rail so that
    parameters such as angle can differ between the two.
    """

    # ── Rail pair ────────────────────────────────────────────────────────────
    rail_spacing: float = 1.435   # centre-to-centre distance, UIC standard gauge
    left_rail: RailConfig = field(default_factory=RailConfig)
    right_rail: RailConfig = field(default_factory=RailConfig)

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
        Nested mappings (e.g. left_rail:) are merged with the field defaults,
        so partial sub-configs are also valid.
        """
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyyaml is required to load geometry config files. "
                "Install it with: pip install pyyaml"
            ) from exc

        import typing

        with open(path, "r", encoding="utf-8") as fh:
            raw: dict = yaml.safe_load(fh) or {}

        # Resolve string annotations (from __future__ annotations) to actual types
        try:
            hints = typing.get_type_hints(cls)
        except Exception:
            hints = {}

        known = {f.name: f for f in dataclasses.fields(cls)}
        overrides: dict[str, Any] = {}
        for key, val in raw.items():
            if key not in known:
                continue
            ftype = hints.get(key)
            # Reconstruct nested dataclasses from YAML mappings (partial ok)
            if (
                ftype is not None
                and dataclasses.is_dataclass(ftype)
                and isinstance(val, dict)
            ):
                inner_known = {f.name for f in dataclasses.fields(ftype)}
                inner_overrides = {k: v for k, v in val.items() if k in inner_known}
                overrides[key] = dataclasses.replace(ftype(), **inner_overrides)
            else:
                overrides[key] = val

        return dataclasses.replace(cls(), **overrides)
