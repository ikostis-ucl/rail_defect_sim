"""The shape every constraint takes.

A constraint answers two questions about a configuration:

  *check*  — is anything wrong, and how would you describe it to a human?
  *repair* — what is the nearest configuration that would not be wrong?

Carrying the repair alongside the check is what lets the system reject a bad
configuration *and propose a working one*, instead of only saying no.

Most constraints are "this quantity must lie between these two values", so
``IntervalConstraint`` provides that shape directly: a subclass supplies the
quantity, the allowed range, and how to write a corrected value back. For an
independent bound, clamping to the interval is not an approximation — it *is*
the nearest valid configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.validation.context import ValidationContext
from app.validation.issue import Severity, ValidationIssue


@dataclass(frozen=True)
class Interval:
    """A closed range of acceptable values. ``None`` means unbounded."""

    low: float | None = None
    high: float | None = None

    def contains(self, value: float) -> bool:
        if self.low is not None and value < self.low:
            return False
        if self.high is not None and value > self.high:
            return False
        return True

    def clamp(self, value: float) -> float:
        """Return the closest value inside the interval."""
        if self.low is not None and value < self.low:
            return self.low
        if self.high is not None and value > self.high:
            return self.high
        return value

    def describe(self, unit: str = "") -> str:
        suffix = f" {unit}" if unit else ""
        if self.low is not None and self.high is not None:
            return f"between {self.low:g}{suffix} and {self.high:g}{suffix}"
        if self.low is not None:
            return f"at least {self.low:g}{suffix}"
        if self.high is not None:
            return f"at most {self.high:g}{suffix}"
        return "any value"


class Constraint(ABC):
    """One rule about a configuration."""

    #: Short identifier, used in reports.
    NAME: str = "constraint"

    #: Dotted paths of the settings this constraint reads, e.g.
    #: ``("geometry.section_pitch", "camera.lens_mm")``. Declared rather than
    #: inferred so the dependency graph can be built mechanically later — a
    #: global solver needs to know which rules touch which variables.
    READS: tuple[str, ...] = ()

    @abstractmethod
    def check(self, ctx: ValidationContext) -> list[ValidationIssue]:
        """Return every problem this constraint finds. Empty means satisfied."""

    def repair(self, ctx: ValidationContext) -> ValidationContext:
        """Return the nearest acceptable configuration.

        Default is to change nothing, which is the honest answer for a
        constraint that can detect a problem but not fix it — the resolver then
        reports it rather than silently pretending it was handled.
        """
        return ctx

    @property
    def repairable(self) -> bool:
        """True when this constraint overrides ``repair``."""
        return type(self).repair is not Constraint.repair

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} {self.NAME}>"


class IntervalConstraint(Constraint):
    """A constraint that one quantity must lie within a range.

    Subclasses provide ``value``, ``interval`` and ``apply`` (plus ``FIELD`` and
    a ``NAME``). Checking and repairing then come for free.
    """

    #: Config field this constraint is about, for reporting.
    FIELD: str = ""

    #: Unit shown in messages, e.g. "m" or "mm".
    UNIT: str = ""

    #: How bad a violation is.
    SEVERITY: Severity = Severity.ERROR

    @abstractmethod
    def value(self, ctx: ValidationContext) -> float:
        """The quantity being constrained."""

    @abstractmethod
    def interval(self, ctx: ValidationContext) -> Interval:
        """The acceptable range, which may depend on the rest of the config."""

    def apply(self, ctx: ValidationContext, value: float) -> ValidationContext:
        """Write *value* back into the configuration.

        Left unimplemented by default: a quantity can be derived from several
        fields with no single obvious one to adjust, and guessing would be worse
        than reporting.
        """
        return ctx

    def explain(self, ctx: ValidationContext, value: float, interval: Interval) -> str:
        return (
            f"{self.FIELD} is {value:g}{' ' + self.UNIT if self.UNIT else ''}; "
            f"expected {interval.describe(self.UNIT)}."
        )

    def check(self, ctx: ValidationContext) -> list[ValidationIssue]:
        value = self.value(ctx)
        interval = self.interval(ctx)
        if interval.contains(value):
            return []
        # Every interval rule reports its numbers as data for free: the value,
        # the bounds and the unit are already here, so a caller never has to
        # read them back out of the sentence.
        return [
            ValidationIssue(
                self.SEVERITY,
                self.FIELD,
                self.explain(ctx, value, interval),
                code=self.NAME,
                value=value,
                expected_min=interval.low,
                expected_max=interval.high,
                unit=self.UNIT,
            )
        ]

    def repair(self, ctx: ValidationContext) -> ValidationContext:
        value = self.value(ctx)
        interval = self.interval(ctx)
        if interval.contains(value):
            return ctx
        return self.apply(ctx, interval.clamp(value))

    @property
    def repairable(self) -> bool:
        return type(self).apply is not IntervalConstraint.apply
