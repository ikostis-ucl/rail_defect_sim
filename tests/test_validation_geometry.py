"""The geometry rules, migrated out of TrackGeometryConfig.validate().

The checks predate this module but were never executed and barely tested — one
test asserted an empty result. These pin each rule at its boundary, then pin the
behaviour that matters more: that the rules now actually run, and that a bad
geometry stops a render instead of building it.
"""

import dataclasses

import pytest

from app.config import PipelineSettings, TrackGeometryConfig
from app.config.geometry import RailConfig
from app.validation import Policy, Resolver, Severity, ValidationError, resolve_or_raise
from app.validation.constraints.geometry import (
    FastenerDoesNotPunchThrough,
    FastenerFitsUnderRail,
    FastenerNotOversized,
    LeftPadThicknessReasonable,
    LeftRailHeightPositive,
    RailsDoNotOverlap,
    RightRailHeightPositive,
    SleeperHeightPositive,
    SleeperNotTooTall,
)
from app.validation.context import ValidationContext


def ctx_for(**geometry_changes) -> ValidationContext:
    geometry = dataclasses.replace(TrackGeometryConfig(), **geometry_changes)
    return ValidationContext.from_settings(PipelineSettings(geometry=geometry))


def fields(issues) -> set[str]:
    return {i.field for i in issues}


# ── The default track is valid ────────────────────────────────────────────────

def test_default_geometry_raises_nothing():
    """Whatever else changes, the shipped default must stay buildable."""
    assert TrackGeometryConfig().validate() == []


def test_default_settings_pass_the_full_resolver():
    assert Resolver().resolve(PipelineSettings()).ok


# ── Errors ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("height", [0.0, -0.1])
def test_non_positive_rail_height_is_an_error(height):
    issues = LeftRailHeightPositive().check(ctx_for(left_rail=RailConfig(height=height)))
    assert len(issues) == 1
    assert issues[0].severity == Severity.ERROR
    assert "positive" in issues[0].message


def test_rail_height_is_checked_per_side():
    """Rails are configured independently, so each is judged independently."""
    ctx = ctx_for(right_rail=RailConfig(height=-1.0))
    assert LeftRailHeightPositive().check(ctx) == []
    assert len(RightRailHeightPositive().check(ctx)) == 1


def test_rail_height_repairs_to_the_standard_not_to_zero():
    """The valid set is open at zero, so clamping would give a useless rail."""
    ctx = ctx_for(left_rail=RailConfig(height=-0.5))
    repaired = LeftRailHeightPositive().repair(ctx)
    assert repaired.geometry.left_rail.height == pytest.approx(0.159)  # UIC54
    assert LeftRailHeightPositive().check(repaired) == []


def test_rail_height_repair_falls_back_when_the_profile_is_unknown():
    ctx = ctx_for(profile="NOPE", left_rail=RailConfig(height=0.0))
    repaired = LeftRailHeightPositive().repair(ctx)
    assert repaired.geometry.left_rail.height == RailConfig().height


def test_non_positive_sleeper_height_is_an_error_and_repairs():
    ctx = ctx_for(sleeper_height=0.0)
    assert len(SleeperHeightPositive().check(ctx)) == 1
    repaired = SleeperHeightPositive().repair(ctx)
    assert repaired.geometry.sleeper_height == pytest.approx(0.200)


def test_rails_overlap_when_gauge_does_not_clear_both_feet():
    ctx = ctx_for(rail_spacing=0.2)   # feet total 0.28
    issues = RailsDoNotOverlap().check(ctx)
    assert len(issues) == 1
    assert "overlap" in issues[0].message
    assert "0.280" in issues[0].message   # reports the number it compared against


def test_gauge_exactly_equal_to_the_feet_still_overlaps():
    """The original bound is strict: touching rails are not acceptable."""
    ctx = ctx_for(rail_spacing=0.280)
    assert len(RailsDoNotOverlap().check(ctx)) == 1


def test_gauge_just_above_the_feet_is_accepted():
    assert RailsDoNotOverlap().check(ctx_for(rail_spacing=0.281)) == []


def test_rails_overlap_is_deliberately_not_repairable():
    """Widening the gauge or narrowing the feet each break a standard."""
    assert not RailsDoNotOverlap().repairable


def test_oversized_fastener_does_not_fit_under_the_rail():
    ctx = ctx_for(screw_radius=0.09)   # diameter 0.18 > foot 0.14
    issues = FastenerFitsUnderRail().check(ctx)
    assert len(issues) == 1
    assert "will not fit" in issues[0].message


def test_fastener_repairs_by_shrinking_to_the_narrowest_foot():
    ctx = ctx_for(screw_radius=0.09)
    repaired = FastenerFitsUnderRail().repair(ctx)
    assert repaired.geometry.screw_radius == pytest.approx(0.070)   # 0.14 / 2
    assert FastenerFitsUnderRail().check(repaired) == []


def test_fastener_uses_the_narrower_of_the_two_feet():
    ctx = ctx_for(right_rail=RailConfig(foot_width=0.05))
    assert FastenerFitsUnderRail().interval(ctx).high == pytest.approx(0.025)


def test_fastener_longer_than_the_sleeper_punches_through():
    ctx = ctx_for(screw_length=0.25)   # sleeper is 0.20 deep
    issues = FastenerDoesNotPunchThrough().check(ctx)
    assert len(issues) == 1
    assert "punch through" in issues[0].message


def test_fastener_exactly_as_long_as_the_sleeper_is_deep_is_an_error():
    assert len(FastenerDoesNotPunchThrough().check(ctx_for(screw_length=0.200))) == 1


def test_fastener_length_repairs_to_sit_inside_the_sleeper():
    """Clamping would seat the clip on the sleeper's underside; 80 % is sane."""
    ctx = ctx_for(screw_length=0.25)
    repaired = FastenerDoesNotPunchThrough().repair(ctx)
    assert repaired.geometry.screw_length == pytest.approx(0.160)
    assert FastenerDoesNotPunchThrough().check(repaired) == []


# ── Warnings ──────────────────────────────────────────────────────────────────

def test_thick_pad_warns_without_blocking():
    ctx = ctx_for(left_rail=RailConfig(pad_thickness=0.10))   # height 0.159
    issues = LeftPadThicknessReasonable().check(ctx)
    assert len(issues) == 1
    assert issues[0].severity == Severity.WARNING


def test_oversized_but_fitting_fastener_only_warns():
    ctx = ctx_for(screw_radius=0.04)   # 0.08 diameter: under 0.14, over 40 % of it
    assert FastenerFitsUnderRail().check(ctx) == []
    assert len(FastenerNotOversized().check(ctx)) == 1


def test_tall_sleeper_warns():
    ctx = ctx_for(sleeper_height=0.5)   # gauge 1.0
    issues = SleeperNotTooTall().check(ctx)
    assert len(issues) == 1
    assert issues[0].severity == Severity.WARNING


@pytest.mark.parametrize(
    "constraint",
    [LeftPadThicknessReasonable, FastenerNotOversized, SleeperNotTooTall],
)
def test_warnings_are_never_repairable(constraint):
    """The resolver repairs anything repairable regardless of severity, so a
    repairable warning would let REPAIR silently rewrite a valid config."""
    assert not constraint().repairable


def test_warnings_do_not_block_a_run():
    settings = PipelineSettings(geometry=TrackGeometryConfig(sleeper_height=0.5))
    report = Resolver().resolve(settings)
    assert report.ok
    assert report.warnings


# ── validate() still works, and now delegates ─────────────────────────────────

def test_validate_still_reports_errors_and_warnings_together():
    cfg = TrackGeometryConfig(rail_spacing=0.2, sleeper_height=0.5)
    issues = cfg.validate()
    assert "rail_spacing" in fields(issues)
    assert any(i.severity == Severity.ERROR for i in issues)
    assert any(i.severity == Severity.WARNING for i in issues)


def test_validate_reports_errors_before_warnings():
    cfg = TrackGeometryConfig(rail_spacing=0.2, sleeper_height=0.5)
    severities = [i.severity for i in cfg.validate()]
    assert severities == sorted(severities, key=lambda s: s != Severity.ERROR)


def test_implausible_pitch_still_passes_validate():
    """Carried over verbatim: the wide_gauge gap is a separate piece of work."""
    cfg = TrackGeometryConfig(sleeper_depth=0.115, section_pitch=0.1855)
    assert cfg.validate() == []


# ── The point of the migration: these now gate a render ───────────────────────

def test_impossible_geometry_stops_a_run():
    settings = PipelineSettings(geometry=TrackGeometryConfig(rail_spacing=0.2))
    with pytest.raises(ValidationError) as excinfo:
        resolve_or_raise(settings, verbose=False)
    assert "overlap" in str(excinfo.value)


def test_repairable_geometry_is_fixed_rather_than_rejected():
    settings = PipelineSettings(geometry=TrackGeometryConfig(screw_radius=0.09))
    resolved = resolve_or_raise(settings, verbose=False)
    assert resolved.geometry.screw_radius == pytest.approx(0.070)


def test_strict_policy_reports_without_touching_the_configuration():
    settings = PipelineSettings(geometry=TrackGeometryConfig(screw_radius=0.09))
    report = Resolver(policy=Policy.STRICT).resolve(settings)
    assert not report.ok
    assert report.settings.geometry.screw_radius == pytest.approx(0.09)


def test_one_repair_does_not_break_another_rule():
    """Shrinking the clip must not trip the oversize warning into an error."""
    settings = PipelineSettings(
        geometry=TrackGeometryConfig(screw_radius=0.09, screw_length=0.3)
    )
    report = Resolver().resolve(settings)
    assert report.ok
    assert report.settings.geometry.screw_radius == pytest.approx(0.070)
    assert report.settings.geometry.screw_length == pytest.approx(0.160)
