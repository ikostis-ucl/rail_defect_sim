"""Dimensions that cannot physically coexist.

These checks are not new — they lived in ``TrackGeometryConfig.validate()``,
which nothing ever called. Expressed as constraints they run on every build, and
they gain repairs: the resolver can now propose a working track instead of only
naming what is wrong.

Two ideas do most of the work here.

**Strict inequalities.** ``Interval`` is closed, but several of these rules are
strict — a rail spacing exactly equal to the combined foot widths still means
the rails touch. ``_STRICT`` is the hair of margin that turns a closed interval
into a strict one, so the migrated checks fire on exactly the inputs the
original code rejected.

**Open bounds have no nearest valid value.** Clamping is the right repair when
the valid set is closed: a clip radius that is too large has an obvious largest
acceptable value. But "height must be positive" is open at zero — the nearest
valid height is an infinitesimal one, which is valid and useless. Those rules
repair to the dimension the *standard* specifies instead, falling back to the
dataclass default when the profile is unknown.
"""

from __future__ import annotations

from app.config.geometry import RailConfig, TrackGeometryConfig
from app.validation.constraint import Interval, IntervalConstraint
from app.validation.context import ValidationContext
from app.validation.issue import Severity

#: Margin that makes a closed ``Interval`` express a strict inequality.
_STRICT = 1e-9

#: Fraction of the limiting dimension a repair targets when the valid set is
#: open, so the repaired value is comfortably inside it rather than on its edge.
_SAFE_FRACTION = 0.8


# ── Per-rail plumbing ─────────────────────────────────────────────────────────

class _RailConstraint(IntervalConstraint):
    """A rule about one rail.

    Left and right rails are configured independently — a defect often affects
    only one — so each rule is registered twice, once per side. ``SIDE`` is the
    only difference, and the registry holds classes rather than instances, so
    two three-line subclasses is the whole cost.
    """

    SIDE: str = "left"

    def rail(self, ctx: ValidationContext) -> RailConfig:
        return getattr(ctx.geometry, f"{self.SIDE}_rail")

    def apply_to_rail(self, ctx: ValidationContext, **changes) -> ValidationContext:
        return getattr(ctx, f"with_{self.SIDE}_rail")(**changes)


# ── Errors: impossible geometry ───────────────────────────────────────────────

class _RailHeightPositive(_RailConstraint):
    """A rail with no height is not a rail."""

    UNIT = "m"

    def value(self, ctx):
        return self.rail(ctx).height

    def interval(self, ctx):
        return Interval(low=_STRICT)

    def apply(self, ctx, value):
        return self.apply_to_rail(ctx, height=value)

    def repair(self, ctx):
        """Repair to the standard height — see the module note on open bounds."""
        if not self.check(ctx):
            return ctx
        profile = ctx.profile
        standard = profile.height_mm / 1000 if profile else RailConfig().height
        return self.apply(ctx, standard)

    def explain(self, ctx, value, interval):
        return "Rail height must be positive."


class LeftRailHeightPositive(_RailHeightPositive):
    NAME = "left_rail_height_positive"
    SIDE = "left"
    FIELD = "left_rail.height"
    READS = ("geometry.left_rail.height",)


class RightRailHeightPositive(_RailHeightPositive):
    NAME = "right_rail_height_positive"
    SIDE = "right"
    FIELD = "right_rail.height"
    READS = ("geometry.right_rail.height",)


class SleeperHeightPositive(IntervalConstraint):
    """A sleeper with no height cannot carry a rail seat."""

    NAME = "sleeper_height_positive"
    FIELD = "sleeper_height"
    UNIT = "m"
    READS = ("geometry.sleeper_height",)

    def value(self, ctx):
        return ctx.geometry.sleeper_height

    def interval(self, ctx):
        return Interval(low=_STRICT)

    def apply(self, ctx, value):
        return ctx.with_geometry(sleeper_height=value)

    def repair(self, ctx):
        if not self.check(ctx):
            return ctx
        return self.apply(ctx, TrackGeometryConfig().sleeper_height)

    def explain(self, ctx, value, interval):
        return "Sleeper height must be positive."


class RailsDoNotOverlap(IntervalConstraint):
    """The gauge must leave room for both rail feet.

    Deliberately **not repairable**. There are two ways out — widen the gauge or
    narrow the feet — and both silently break a standard the configuration is
    claiming to follow: the gauge *is* the track standard, and foot width comes
    from the rail profile. Guessing which the user meant is worse than stopping,
    so this one fails the run and says why.
    """

    NAME = "rails_do_not_overlap"
    FIELD = "rail_spacing"
    UNIT = "m"
    READS = (
        "geometry.rail_spacing",
        "geometry.left_rail.foot_width",
        "geometry.right_rail.foot_width",
    )

    def _combined_feet(self, ctx) -> float:
        return ctx.geometry.left_rail.foot_width + ctx.geometry.right_rail.foot_width

    def value(self, ctx):
        return ctx.geometry.rail_spacing

    def interval(self, ctx):
        return Interval(low=self._combined_feet(ctx) + _STRICT)

    def explain(self, ctx, value, interval):
        return (
            f"Rail spacing ({value:.3f} m) must exceed combined foot widths "
            f"({self._combined_feet(ctx):.3f} m) — rails would overlap."
        )


class FastenerFitsUnderRail(IntervalConstraint):
    """A clip wider than the rail foot has nowhere to sit."""

    NAME = "fastener_fits_under_rail"
    FIELD = "screw_radius"
    UNIT = "m"
    READS = (
        "geometry.screw_radius",
        "geometry.left_rail.foot_width",
        "geometry.right_rail.foot_width",
    )

    def _narrowest_foot(self, ctx) -> float:
        return min(ctx.geometry.left_rail.foot_width, ctx.geometry.right_rail.foot_width)

    def value(self, ctx):
        return ctx.geometry.screw_radius

    def interval(self, ctx):
        return Interval(high=self._narrowest_foot(ctx) / 2)

    def apply(self, ctx, value):
        return ctx.with_geometry(screw_radius=value)

    def explain(self, ctx, value, interval):
        return (
            "Fastener diameter exceeds rail foot width — "
            "clips will not fit under the rail."
        )


class FastenerDoesNotPunchThrough(IntervalConstraint):
    """A clip as long as the sleeper is deep would come out the bottom."""

    NAME = "fastener_does_not_punch_through"
    FIELD = "screw_length"
    UNIT = "m"
    READS = ("geometry.screw_length", "geometry.sleeper_height")

    def value(self, ctx):
        return ctx.geometry.screw_length

    def interval(self, ctx):
        return Interval(high=ctx.geometry.sleeper_height - _STRICT)

    def apply(self, ctx, value):
        return ctx.with_geometry(screw_length=value)

    def repair(self, ctx):
        """Seat the clip well inside the sleeper.

        The bound is strict, so clamping would land a hair under the sleeper
        height — arithmetically nearest, and a clip that reaches the underside
        of the sleeper. See the module note on open bounds.
        """
        if not self.check(ctx):
            return ctx
        return self.apply(ctx, ctx.geometry.sleeper_height * _SAFE_FRACTION)

    def explain(self, ctx, value, interval):
        return (
            "Fastener length equals or exceeds sleeper height — "
            "clip would punch through sleeper."
        )


# ── Warnings: unusual but renderable ──────────────────────────────────────────
#
# None of these define ``apply``, so none are repairable. That is deliberate:
# the resolver repairs anything repairable regardless of severity, so giving a
# warning a repair would let REPAIR policy silently rewrite a configuration that
# was merely unusual. They report, and the run proceeds.

class _PadThicknessReasonable(_RailConstraint):
    """A pad half as thick as the rail is tall is not a pad any more."""

    UNIT = "m"
    SEVERITY = Severity.WARNING

    def value(self, ctx):
        return self.rail(ctx).pad_thickness

    def interval(self, ctx):
        return Interval(high=self.rail(ctx).height * 0.5 - _STRICT)

    def explain(self, ctx, value, interval):
        return "Rail pad thickness is unusually large (≥ 50 % of rail height)."


class LeftPadThicknessReasonable(_PadThicknessReasonable):
    NAME = "left_pad_thickness_reasonable"
    SIDE = "left"
    FIELD = "left_rail.pad_thickness"
    READS = ("geometry.left_rail.pad_thickness", "geometry.left_rail.height")


class RightPadThicknessReasonable(_PadThicknessReasonable):
    NAME = "right_pad_thickness_reasonable"
    SIDE = "right"
    FIELD = "right_rail.pad_thickness"
    READS = ("geometry.right_rail.pad_thickness", "geometry.right_rail.height")


class FastenerNotOversized(IntervalConstraint):
    """Fits, but dominates the rail foot."""

    NAME = "fastener_not_oversized"
    FIELD = "screw_radius"
    UNIT = "m"
    SEVERITY = Severity.WARNING
    READS = (
        "geometry.screw_radius",
        "geometry.left_rail.foot_width",
        "geometry.right_rail.foot_width",
    )

    def value(self, ctx):
        return ctx.geometry.screw_radius

    def interval(self, ctx):
        narrowest = min(
            ctx.geometry.left_rail.foot_width, ctx.geometry.right_rail.foot_width
        )
        return Interval(high=narrowest * 0.4 / 2)

    def explain(self, ctx, value, interval):
        return (
            "Fastener diameter exceeds 40 % of rail foot width — "
            "clips are unusually large."
        )


class SleeperNotTooTall(IntervalConstraint):
    """A sleeper deep relative to the gauge looks wrong even if it builds."""

    NAME = "sleeper_not_too_tall"
    FIELD = "sleeper_height"
    UNIT = "m"
    SEVERITY = Severity.WARNING
    READS = ("geometry.sleeper_height", "geometry.rail_spacing")

    def value(self, ctx):
        return ctx.geometry.sleeper_height

    def interval(self, ctx):
        return Interval(high=ctx.geometry.rail_spacing * 0.3)

    def explain(self, ctx, value, interval):
        return (
            "Sleeper height exceeds 30 % of gauge — "
            "unusually tall relative to track width."
        )


#: Registration order, which is also the order issues are reported in — errors
#: before warnings, matching what ``validate()`` has always produced.
GEOMETRY_CONSTRAINTS: list[type[IntervalConstraint]] = [
    LeftRailHeightPositive,
    RightRailHeightPositive,
    SleeperHeightPositive,
    RailsDoNotOverlap,
    FastenerFitsUnderRail,
    FastenerDoesNotPunchThrough,
    LeftPadThicknessReasonable,
    RightPadThicknessReasonable,
    FastenerNotOversized,
    SleeperNotTooTall,
]
