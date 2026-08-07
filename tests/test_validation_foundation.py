"""The validation machinery: context, constraints, resolver.

No real rules exist yet — those are separate pieces of work — so these tests
define their own throwaway constraints to exercise the mechanism. That is
deliberate: it keeps the foundation tested independently of whatever rules end
up being written on top of it.
"""

import pytest

from app.config import CameraConfig, PipelineSettings, RenderConfig, TrackGeometryConfig
from app.validation import (
    Constraint,
    Interval,
    IntervalConstraint,
    Policy,
    Resolver,
    Severity,
    ValidationContext,
    ValidationError,
    all_constraints,
    resolve_or_raise,
)
from app.validation.issue import error, warning


# ── Test doubles ──────────────────────────────────────────────────────────────

class AlwaysFails(Constraint):
    NAME = "always_fails"

    def check(self, ctx):
        return [error("test.field", "this always fails")]


class AlwaysWarns(Constraint):
    NAME = "always_warns"

    def check(self, ctx):
        return [warning("test.field", "this is only a warning")]


class LensAtLeast35(IntervalConstraint):
    """Repairable: clamps the lens up to 35 mm."""

    NAME = "lens_min"
    FIELD = "camera.lens_mm"
    UNIT = "mm"
    READS = ("camera.lens_mm",)

    def value(self, ctx):
        return ctx.camera.lens_mm

    def interval(self, ctx):
        return Interval(low=35.0)

    def apply(self, ctx, value):
        return ctx.with_camera(lens_mm=value)


class TrackLongerThanTravel(IntervalConstraint):
    """Cross-config: reads camera motion and track length together."""

    NAME = "track_covers_travel"
    FIELD = "track_length"
    UNIT = "m"
    READS = ("track_length", "base_speed_units_per_frame", "render.duration_seconds")

    def value(self, ctx):
        return float(ctx.settings.track_length)

    def interval(self, ctx):
        return Interval(low=ctx.settings.total_travel_distance)

    def apply(self, ctx, value):
        return ctx.with_settings(track_length=int(value))


# ── ValidationContext ─────────────────────────────────────────────────────────

def test_context_exposes_every_config():
    ctx = ValidationContext.from_settings(PipelineSettings())
    assert isinstance(ctx.geometry, TrackGeometryConfig)
    assert isinstance(ctx.camera, CameraConfig)
    assert isinstance(ctx.render, RenderConfig)


def test_context_resolves_the_active_rail_profile():
    """The point of the profile field: the standard is now identifiable."""
    ctx = ValidationContext.from_settings(PipelineSettings())
    assert ctx.profile is not None
    assert ctx.profile.name == "UIC54"


def test_unknown_profile_yields_none_rather_than_inventing_one():
    settings = PipelineSettings(geometry=TrackGeometryConfig(profile="NOPE"))
    assert ValidationContext.from_settings(settings).profile is None


def test_with_helpers_return_modified_copies():
    ctx = ValidationContext.from_settings(PipelineSettings())
    changed = ctx.with_camera(lens_mm=85.0)
    assert changed.camera.lens_mm == 85.0
    assert ctx.camera.lens_mm == 35.0          # original untouched
    assert changed.render == ctx.render        # other domains untouched


def test_with_geometry_and_rail_helpers():
    ctx = ValidationContext.from_settings(PipelineSettings())
    assert ctx.with_geometry(section_pitch=0.5).geometry.section_pitch == 0.5
    assert ctx.with_left_rail(height=0.2).geometry.left_rail.height == 0.2
    assert ctx.with_left_rail(height=0.2).geometry.right_rail.height == 0.159


def test_context_spans_configs_that_never_meet_elsewhere():
    """A camera-vs-geometry rule is expressible only because of the context."""
    ctx = ValidationContext.from_settings(PipelineSettings())
    clearance = ctx.camera.resolve_world_height(ctx.geometry.rail_top_z)
    assert clearance == pytest.approx(2.45)


# ── Interval ──────────────────────────────────────────────────────────────────

def test_interval_contains_and_clamps():
    iv = Interval(low=1.0, high=2.0)
    assert iv.contains(1.5) and not iv.contains(0.5) and not iv.contains(2.5)
    assert iv.clamp(0.5) == 1.0
    assert iv.clamp(2.5) == 2.0
    assert iv.clamp(1.5) == 1.5


def test_interval_open_ended():
    assert Interval(low=1.0).contains(1e9)
    assert Interval(high=1.0).contains(-1e9)
    assert Interval().contains(0.0)


def test_interval_describes_itself():
    assert "between" in Interval(1, 2).describe()
    assert "at least" in Interval(low=1).describe()
    assert "at most" in Interval(high=2).describe()


# ── Constraint basics ─────────────────────────────────────────────────────────

def test_constraint_without_repair_is_not_repairable():
    assert not AlwaysFails().repairable


def test_interval_constraint_with_apply_is_repairable():
    assert LensAtLeast35().repairable


def test_constraints_declare_what_they_read():
    """Needed later to build the dependency graph mechanically."""
    assert "camera.lens_mm" in LensAtLeast35().READS


def test_interval_constraint_passes_when_satisfied():
    ctx = ValidationContext.from_settings(PipelineSettings())
    assert LensAtLeast35().check(ctx) == []


def test_interval_constraint_reports_value_and_range():
    settings = PipelineSettings(camera=CameraConfig(lens_mm=24.0))
    issues = LensAtLeast35().check(ValidationContext.from_settings(settings))
    assert len(issues) == 1
    assert "24" in issues[0].message and "35" in issues[0].message
    assert issues[0].severity == Severity.ERROR


# ── Resolver: empty registry ──────────────────────────────────────────────────

def test_shipped_registry_is_empty_for_now():
    assert all_constraints() == []


def test_empty_constraint_set_is_a_no_op():
    settings = PipelineSettings()
    report = Resolver([]).resolve(settings)
    assert report.ok
    assert report.settings == settings
    assert report.render() == "Configuration OK."


def test_default_resolver_accepts_the_default_configuration():
    """With no rules registered, a stock render must not be blocked."""
    assert Resolver().resolve(PipelineSettings()).ok


# ── Resolver: repair policy ───────────────────────────────────────────────────

def test_repair_clamps_and_reports_the_change():
    settings = PipelineSettings(camera=CameraConfig(lens_mm=24.0))
    report = Resolver([LensAtLeast35()]).resolve(settings)
    assert report.ok
    assert report.settings.camera.lens_mm == 35.0
    assert len(report.repairs) == 1
    assert report.repairs[0].field == "camera.lens_mm"
    assert report.repairs[0].before == "24" and report.repairs[0].after == "35"


def test_repair_leaves_untouched_settings_alone():
    settings = PipelineSettings(camera=CameraConfig(lens_mm=24.0), track_length=500)
    report = Resolver([LensAtLeast35()]).resolve(settings)
    assert report.settings.track_length == 500
    assert report.settings.seed == settings.seed


def test_unrepairable_error_is_reported_as_unresolved():
    report = Resolver([AlwaysFails()]).resolve(PipelineSettings())
    assert not report.ok
    assert len(report.unresolved) == 1
    assert "always fails" in report.render()


def test_warnings_do_not_block():
    report = Resolver([AlwaysWarns()]).resolve(PipelineSettings())
    assert report.ok
    assert len(report.warnings) == 1
    assert not report.errors


def test_cross_config_repair():
    """A rule reading camera motion adjusts track length to match."""
    settings = PipelineSettings(
        render=RenderConfig(fps=10, duration_seconds=10),   # 100 frames
        base_speed_units_per_frame=2.5,                     # 250 m of travel
        track_length=100,                                   # too short
    )
    report = Resolver([TrackLongerThanTravel()]).resolve(settings)
    assert report.ok
    assert report.settings.track_length == 250


# ── Resolver: strict and warn ─────────────────────────────────────────────────

def test_strict_policy_refuses_without_adjusting():
    settings = PipelineSettings(camera=CameraConfig(lens_mm=24.0))
    report = Resolver([LensAtLeast35()], policy=Policy.STRICT).resolve(settings)
    assert not report.ok
    assert report.settings.camera.lens_mm == 24.0   # untouched
    assert report.repairs == []


def test_warn_policy_proceeds_and_changes_nothing():
    settings = PipelineSettings(camera=CameraConfig(lens_mm=24.0))
    report = Resolver([LensAtLeast35()], policy=Policy.WARN).resolve(settings)
    assert report.ok
    assert report.settings.camera.lens_mm == 24.0
    assert len(report.issues) == 1


# ── Resolver: conflicting constraints ─────────────────────────────────────────

def test_conflicting_repairs_are_reported_not_spun_on():
    """Two rules pushing the same value apart must terminate and say so."""

    class LensAtLeast50(LensAtLeast35):
        NAME = "lens_min_50"

        def interval(self, ctx):
            return Interval(low=50.0)

    class LensAtMost40(LensAtLeast35):
        NAME = "lens_max_40"

        def interval(self, ctx):
            return Interval(high=40.0)

    settings = PipelineSettings(camera=CameraConfig(lens_mm=45.0))
    report = Resolver([LensAtLeast50(), LensAtMost40()], max_rounds=5).resolve(settings)
    assert not report.ok
    assert report.exhausted_rounds
    assert "conflict" in report.render()


def test_resolver_terminates_on_conflict_rather_than_hanging():
    class Grow(IntervalConstraint):
        NAME = "grow"
        FIELD = "track_length"

        def value(self, ctx):
            return float(ctx.settings.track_length)

        def interval(self, ctx):
            return Interval(low=ctx.settings.track_length + 1)

        def apply(self, ctx, value):
            return ctx.with_settings(track_length=int(value))

    report = Resolver([Grow()], max_rounds=3).resolve(PipelineSettings(track_length=10))
    assert report.exhausted_rounds
    assert report.settings.track_length == 13   # advanced once per round, then gave up


# ── resolve_or_raise ──────────────────────────────────────────────────────────

def test_resolve_or_raise_returns_repaired_settings():
    settings = PipelineSettings(camera=CameraConfig(lens_mm=24.0))
    resolved = resolve_or_raise(settings, constraints=[LensAtLeast35()], verbose=False)
    assert resolved.camera.lens_mm == 35.0


def test_resolve_or_raise_raises_on_unresolvable():
    with pytest.raises(ValidationError) as excinfo:
        resolve_or_raise(PipelineSettings(), constraints=[AlwaysFails()], verbose=False)
    assert "always fails" in str(excinfo.value)
    assert excinfo.value.report.unresolved


def test_resolve_or_raise_is_a_no_op_with_no_constraints():
    settings = PipelineSettings()
    assert resolve_or_raise(settings, constraints=[], verbose=False) == settings
