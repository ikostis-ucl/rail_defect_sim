"""
Track geometry configuration — single source of truth for all dimensions.

All values are in metres (1 Blender unit = 1 m).
Load from a YAML file with TrackGeometryConfig.from_yaml(path), or derive
a physically coherent config from a track gauge and rail profile with
TrackGeometryConfig.from_gauge(gauge_mm, profile="UIC54").
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RailConfig:
    """
    Geometry for a single rail cross-section.

    Each rail is configured independently, allowing the left and right rails
    to have different dimensions or angles (e.g. for defect simulation).

    Physical meaning of each field (all in metres):
      head_width    — width of the rail crown (the running surface a wheel
                      contacts); determines the visual width of the rail mesh.
      foot_width    — width of the base flange that rests on the sleeper;
                      this is always wider than head_width and drives the
                      sleeper overhang and fastener seat positions.
      height        — total rail height from base of foot to top of head.
      pad_thickness — thickness of the elastomeric pad inserted between the
                      rail foot and the sleeper surface; raises the rail seat
                      and isolates vibration.
      lift          — extra clearance above the nominal rail seat; used by
                      defect simulation only (not a physical rail property).
      angle         — rotation around the vertical (Z) axis in degrees;
                      0 = rail aligned with track direction (normal operation);
                      non-zero = rail skewed in the horizontal plane (defect).
    """

    head_width: float = 0.070     # rail crown width — visual width of the rail top
    foot_width: float = 0.140     # base flange width — determines sleeper overhang and fastener seats
    height: float = 0.159         # total rail height (foot bottom to head top)
    pad_thickness: float = 0.007  # elastomeric pad between rail foot and sleeper surface
    lift: float = 0.0             # defect-use only: extra clearance above the rail seat
    angle: float = 0.0            # defect-use only: horizontal skew in degrees


@dataclass(frozen=True)
class ValidationIssue:
    """One entry returned by TrackGeometryConfig.validate()."""

    severity: str   # "error" | "warning"
    field: str      # which config field is implicated
    message: str    # human-readable description


@dataclass(frozen=True)
class TrackGeometryConfig:
    """
    Frozen dataclass holding every geometric parameter for one track section.

    section_pitch (the centre-to-centre spacing between consecutive sleeper
    positions) is a *derived* quantity:

        section_pitch = sleeper_depth / sleeper_pitch_ratio

    Changing sleeper_depth or sleeper_pitch_ratio automatically adjusts the
    pitch — the two values cannot drift apart.

    Each rail is configured independently via left_rail / right_rail.

    Use from_gauge(gauge_mm, profile) to build a physically coherent config
    from a single gauge value and a standard rail profile (UIC54, UIC60, 115RE).
    Use validate() to check for physically impossible combinations.
    """

    # ── Rail pair ─────────────────────────────────────────────────────────────
    rail_spacing: float = 1.000   # track gauge: centre-to-centre distance between rail centrelines
    left_rail: RailConfig = field(default_factory=RailConfig)
    right_rail: RailConfig = field(default_factory=RailConfig)

    # ── Sleeper ───────────────────────────────────────────────────────────────
    # sleeper_depth: along-track extent of the sleeper body (its "thickness" seen
    # from the side of the track).  For Camrail concrete monoblock: 200 mm.
    # clear gap between adjacent sleepers = section_pitch − sleeper_depth.
    # At 600 mm pitch: 600 − 200 = 400 mm clear gap.
    sleeper_depth: float = 0.200

    sleeper_height: float = 0.200  # vertical sleeper dimension (Z axis)

    # Fraction of the centre-to-centre pitch occupied by the sleeper body.
    # section_pitch = sleeper_depth / sleeper_pitch_ratio
    # Default: 0.200 / 0.320 = 0.625 m  (mid-range of 600–660 mm Camrail spec,
    #   yielding 1 600 sleepers/km — within the 1 500–1 666 sleepers/km target)
    sleeper_pitch_ratio: float = 0.320

    # ── Fasteners ─────────────────────────────────────────────────────────────
    screw_radius: float = 0.0065   # radius of the elastic clip cylinder (clip diameter / 2)
    screw_length: float = 0.035    # height of the clip above the sleeper surface

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def section_pitch(self) -> float:
        """Centre-to-centre distance between consecutive sleeper positions (m)."""
        return self.sleeper_depth / self.sleeper_pitch_ratio

    # ── Validation ────────────────────────────────────────────────────────────

    def validate(self) -> list[ValidationIssue]:
        """Check for physically implausible dimension combinations.

        Returns a (possibly empty) list of ValidationIssue objects.
        Severity "error" means the geometry is geometrically impossible;
        severity "warning" means the combination is unusual but renderable.
        Never raises — callers decide what to do with the issues.
        """
        issues: list[ValidationIssue] = []
        lr, rr = self.left_rail, self.right_rail

        # ── Errors (impossible geometry) ──────────────────────────────────────
        if lr.height <= 0 or rr.height <= 0:
            issues.append(ValidationIssue(
                "error", "rail.height", "Rail height must be positive."))

        if self.sleeper_height <= 0:
            issues.append(ValidationIssue(
                "error", "sleeper_height", "Sleeper height must be positive."))

        if self.rail_spacing <= lr.foot_width + rr.foot_width:
            issues.append(ValidationIssue(
                "error", "rail_spacing",
                f"Rail spacing ({self.rail_spacing:.3f} m) must exceed combined foot widths "
                f"({lr.foot_width + rr.foot_width:.3f} m) — rails would overlap."))

        if self.screw_radius * 2 > min(lr.foot_width, rr.foot_width):
            issues.append(ValidationIssue(
                "error", "screw_radius",
                "Fastener diameter exceeds rail foot width — clips will not fit under the rail."))

        if self.screw_length >= self.sleeper_height:
            issues.append(ValidationIssue(
                "error", "screw_length",
                "Fastener length equals or exceeds sleeper height — clip would punch through sleeper."))

        # ── Warnings (unusual but renderable) ─────────────────────────────────
        if lr.pad_thickness >= lr.height * 0.5 or rr.pad_thickness >= rr.height * 0.5:
            issues.append(ValidationIssue(
                "warning", "rail.pad_thickness",
                "Rail pad thickness is unusually large (≥ 50 % of rail height)."))

        if self.screw_radius * 2 > min(lr.foot_width, rr.foot_width) * 0.4:
            issues.append(ValidationIssue(
                "warning", "screw_radius",
                "Fastener diameter exceeds 40 % of rail foot width — clips are unusually large."))

        if self.sleeper_height > self.rail_spacing * 0.3:
            issues.append(ValidationIssue(
                "warning", "sleeper_height",
                "Sleeper height exceeds 30 % of gauge — unusually tall relative to track width."))

        return issues

    # ── Profile validation ────────────────────────────────────────────────────

    def validate_against_profile(
        self,
        profile_name: str,
        tolerance: float = 0.15,
    ) -> tuple["TrackGeometryConfig", list[ValidationIssue]]:
        """Check every dimension against the named profile's standard values.

        Returns ``(adjusted_config, issues)``.

        Fields that deviate by more than *tolerance* fraction from the profile
        standard are clamped to the standard value; a warning ValidationIssue
        is added for each adjustment.

        If *profile_name* is not in the catalog, returns ``(self, [])`` —
        no standard values are on record so all input values are accepted as-is.

        TODO (TSV-269): Replace this per-field independent check with a proper
        Constrained Programming solver that finds the globally consistent set of
        dimensions satisfying ALL profile constraints simultaneously.  The current
        approach processes fields independently, which can mask constraint
        interactions (e.g. adjusting foot_width alone may violate the
        rail_spacing overlap invariant that validate() enforces).
        """
        from app.config.profiles import PROFILES
        if profile_name not in PROFILES:
            return self, []

        p = PROFILES[profile_name]
        issues: list[ValidationIssue] = []

        def _check(field: str, actual_m: float, standard_mm: float) -> float:
            expected = standard_mm / 1000
            if expected <= 0:
                return actual_m
            deviation = abs(actual_m - expected) / expected
            if deviation > tolerance:
                issues.append(ValidationIssue(
                    "warning", field,
                    f"value {actual_m:.4f} m deviates {deviation:.0%} from "
                    f"{profile_name} standard ({expected:.4f} m); adjusted.",
                ))
                return expected
            return actual_m

        new_lr = dataclasses.replace(
            self.left_rail,
            head_width=_check("left_rail.head_width", self.left_rail.head_width, p.head_width_mm),
            foot_width=_check("left_rail.foot_width", self.left_rail.foot_width, p.foot_width_mm),
            height=_check("left_rail.height", self.left_rail.height, p.height_mm),
            pad_thickness=_check("left_rail.pad_thickness", self.left_rail.pad_thickness, p.pad_thickness_mm),
        )
        new_rr = dataclasses.replace(
            self.right_rail,
            head_width=_check("right_rail.head_width", self.right_rail.head_width, p.head_width_mm),
            foot_width=_check("right_rail.foot_width", self.right_rail.foot_width, p.foot_width_mm),
            height=_check("right_rail.height", self.right_rail.height, p.height_mm),
            pad_thickness=_check("right_rail.pad_thickness", self.right_rail.pad_thickness, p.pad_thickness_mm),
        )

        adjusted = dataclasses.replace(
            self,
            left_rail=new_lr,
            right_rail=new_rr,
            sleeper_depth=_check("sleeper_depth", self.sleeper_depth, p.sleeper_depth_mm),
            sleeper_height=_check("sleeper_height", self.sleeper_height, p.sleeper_height_mm),
            screw_radius=_check("screw_radius", self.screw_radius, p.clip_diameter_mm / 2),
            screw_length=_check("screw_length", self.screw_length, p.clip_height_mm),
        )
        return adjusted, issues

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict of all fields (suitable for cache key hashing)."""
        return dataclasses.asdict(self)

    # ── Construction ──────────────────────────────────────────────────────────

    @classmethod
    def from_gauge(cls, gauge_mm: float, profile: str | None = None) -> "TrackGeometryConfig":
        """Build a fully coherent geometry config from a gauge and rail profile.

        gauge_mm  — track gauge in millimetres (e.g. 1000 for metre gauge,
                    1435 for UIC standard gauge).
        profile   — name of a rail profile in the catalog (UIC54, UIC60, 115RE).

        All dimensions are derived from the profile spec; the gauge controls
        rail_spacing and — indirectly — sleeper_pitch_ratio so that
        section_pitch targets the standard 625 mm centre-to-centre spacing.
        """
        from app.config.profiles import DEFAULT_PROFILE, PROFILES
        if profile is None:
            profile = DEFAULT_PROFILE
        if profile not in PROFILES:
            raise ValueError(
                f"Unknown rail profile {profile!r}. "
                f"Known profiles: {sorted(PROFILES)}"
            )
        p = PROFILES[profile]
        rail_cfg = RailConfig(
            head_width=p.head_width_mm / 1000,
            foot_width=p.foot_width_mm / 1000,
            height=p.height_mm / 1000,
            pad_thickness=p.pad_thickness_mm / 1000,
        )
        return cls(
            rail_spacing=gauge_mm / 1000,
            left_rail=rail_cfg,
            right_rail=rail_cfg,
            sleeper_depth=p.sleeper_depth_mm / 1000,
            sleeper_height=p.sleeper_height_mm / 1000,
            sleeper_pitch_ratio=p.sleeper_pitch_ratio,
            screw_radius=p.clip_diameter_mm / 2 / 1000,
            screw_length=p.clip_height_mm / 1000,
        )

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
