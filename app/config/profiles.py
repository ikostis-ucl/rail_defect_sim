"""
Rail profile catalog — standard values for known rail profile types.

Each profile is the *reference* used by
``TrackGeometryConfig.validate_against_profile()``: if a user-supplied geometry
config deviates from these values beyond a tolerance, each outlier dimension is
adjusted and a warning is emitted.  If the requested profile name is not found,
all user values are accepted as-is.

**Separation of concerns** — profile specs (this file / ``configs/profiles/``)
are separate from input dimension configs (``configs/geometry/``).  The profile
files describe *what the standard says*; the geometry files describe *what you
want to render*.  The validation step bridges the two.

YAML override: files in ``configs/profiles/*.yml`` are loaded at import time and
override the built-in Python dicts, so new profiles can be added or existing
ones tuned without touching source code.

Sources:
  UIC54 (54E1)  — UIC leaflet 860, Table 1; Camrail sleeper specification
  UIC60 (60E1)  — UIC leaflet 860, Table 1
  115RE         — AREMA Manual for Railway Engineering, Chapter 4
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class RailProfileSpec:
    """
    Standard values for one rail profile.  Used as a reference by
    ``TrackGeometryConfig.validate_against_profile()``.

    All linear dimensions are in millimetres.
    ``sleeper_pitch_ratio`` is dimensionless:
        section_pitch [m] = (sleeper_depth_mm / 1000) / sleeper_pitch_ratio
    """

    name: str               # short identifier, doubles as catalog key (e.g. "UIC54")
    standard: str           # official designation (e.g. "54E1")

    # ── Rail cross-section (gauge-independent absolute values) ────────────────
    head_width_mm: float    # rail crown width — top running surface
    foot_width_mm: float    # base flange width — determines fastener seat positions
    height_mm: float        # total rail height (foot bottom to head top)

    # ── Sleeper ───────────────────────────────────────────────────────────────
    # sleeper_depth_mm: along-track extent of the sleeper body.
    # Together with sleeper_pitch_ratio it determines centre-to-centre pitch:
    #   section_pitch [m] = (sleeper_depth_mm / 1000) / sleeper_pitch_ratio
    #
    # clear gap between adjacent sleepers = section_pitch - sleeper_depth_mm/1000
    sleeper_depth_mm: float

    sleeper_height_mm: float    # vertical sleeper dimension (Z axis)

    # sleeper_pitch_ratio: fraction of section_pitch occupied by the sleeper body.
    # Equivalently: sleeper_depth / section_pitch.  Must be in (0, 1).
    sleeper_pitch_ratio: float

    # ── Fasteners ─────────────────────────────────────────────────────────────
    clip_diameter_mm: float     # elastic spring-steel clip rod diameter
    clip_height_mm: float       # clip protrusion above sleeper surface
    pad_thickness_mm: float     # elastomeric pad between rail foot and sleeper surface


# Default profile used by TrackGeometryConfig.from_gauge() when no profile is specified.
DEFAULT_PROFILE = "UIC54"


# ── YAML loader ───────────────────────────────────────────────────────────────

def _load_profiles_from_dir(profiles_dir: Path) -> Dict[str, RailProfileSpec]:
    """Load every *.yml in profiles_dir into RailProfileSpec objects.

    Unknown YAML keys are silently ignored so that commentary fields can live
    in the file without breaking parsing.  Missing *required* fields raise a
    warning and skip that file.
    Returns an empty dict when pyyaml is absent or profiles_dir does not exist.
    """
    try:
        import yaml
    except ModuleNotFoundError:
        return {}

    if not profiles_dir.is_dir():
        return {}

    _fields = {f.name for f in RailProfileSpec.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    result: Dict[str, RailProfileSpec] = {}

    for yml_path in sorted(profiles_dir.glob("*.yml")):
        try:
            with yml_path.open("r", encoding="utf-8") as fh:
                data: dict = yaml.safe_load(fh) or {}
            missing = _fields - data.keys()
            if missing:
                raise ValueError(f"missing required fields: {sorted(missing)}")
            spec = RailProfileSpec(**{k: data[k] for k in _fields})
            result[spec.name] = spec
        except Exception as exc:
            warnings.warn(
                f"Could not load rail profile {yml_path.name}: {exc}",
                stacklevel=2,
            )

    return result


# ── Built-in profiles ─────────────────────────────────────────────────────────

def _builtin_profiles() -> Dict[str, RailProfileSpec]:
    return {
        # 54E1 / UIC54 — Camrail metre-gauge mainlines (Cameroon).
        #
        # Sleeper: Camrail concrete monoblock.
        #   Along-track depth (sleeper_depth) = 200 mm.
        #   Centre-to-centre pitch range: 600–660 mm → 1 500–1 666 sleepers/km.
        #   Clear gap at 600 mm pitch: 600 − 200 = 400 mm.
        #   section_pitch = 0.200 / 0.320 = 0.625 m  (mid-range of Camrail spec)
        "UIC54": RailProfileSpec(
            name="UIC54",
            standard="54E1",
            head_width_mm=70.0,
            foot_width_mm=140.0,
            height_mm=159.0,
            sleeper_depth_mm=200.0,
            sleeper_height_mm=200.0,
            sleeper_pitch_ratio=0.320,   # 200 mm / 625 mm = 0.320
            clip_diameter_mm=13.0,
            clip_height_mm=30.0,
            pad_thickness_mm=7.0,
        ),

        # 60E1 / UIC60 — European high-speed and heavy-haul mainlines at 1 435 mm gauge.
        #   Concrete monoblock B70 sleeper: 260 mm along-track depth.
        #   section_pitch = 0.260 / 0.400 = 0.650 m
        "UIC60": RailProfileSpec(
            name="UIC60",
            standard="60E1",
            head_width_mm=74.0,
            foot_width_mm=150.0,
            height_mm=172.0,
            sleeper_depth_mm=260.0,
            sleeper_height_mm=220.0,
            sleeper_pitch_ratio=0.400,   # 260 mm / 650 mm = 0.400
            clip_diameter_mm=13.0,
            clip_height_mm=30.0,
            pad_thickness_mm=7.0,
        ),

        # 115RE — AREMA North American Class I freight mainlines at 1 435 mm gauge.
        #   Concrete crosstie: 260 mm along-track depth at 600 mm pitch.
        #   section_pitch = 0.260 / 0.433 ≈ 0.600 m
        "115RE": RailProfileSpec(
            name="115RE",
            standard="AREMA 115RE",
            head_width_mm=69.9,
            foot_width_mm=152.4,
            height_mm=184.2,
            sleeper_depth_mm=260.0,
            sleeper_height_mm=210.0,
            sleeper_pitch_ratio=0.433,   # 260 mm / 600 mm ≈ 0.433
            clip_diameter_mm=14.0,
            clip_height_mm=35.0,
            pad_thickness_mm=8.0,
        ),
    }


# ── Catalog assembly ──────────────────────────────────────────────────────────

def _load_profiles() -> Dict[str, RailProfileSpec]:
    """Merge built-ins with any YAML files found in configs/profiles/.

    YAML files take precedence: a YAML whose ``name`` field matches a built-in
    overrides that built-in, so operators can tune standards without modifying
    Python source.
    """
    built_in = _builtin_profiles()
    profiles_dir = Path(__file__).parents[2] / "configs" / "profiles"
    from_yaml = _load_profiles_from_dir(profiles_dir)
    return {**built_in, **from_yaml}


# Catalog keyed by the ``name`` field of each profile (e.g. "UIC54").
PROFILES: Dict[str, RailProfileSpec] = _load_profiles()
