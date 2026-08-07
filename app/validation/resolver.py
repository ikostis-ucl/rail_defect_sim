"""Run the constraints, repair what can be repaired, report what happened.

The algorithm is deliberately simple: check everything, clamp each violation to
the nearest acceptable value, then check again, until nothing changes. For a
constraint that stands alone, clamping *is* the optimal repair, so most of the
work needs nothing cleverer.

Where it stops short is interacting constraints — fixing one field can violate
another, and two rules can push the same value back and forth forever. The
round cap is what makes that safe: the resolver gives up and **reports the
conflict** rather than spinning or pretending it converged. Finding the nearest
configuration satisfying every rule *simultaneously* is a different kind of
problem, deferred to the constraint-solver work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.config import PipelineSettings
from app.validation.constraint import Constraint
from app.validation.context import ValidationContext
from app.validation.issue import Severity, ValidationIssue

DEFAULT_MAX_ROUNDS = 10


class Policy(StrEnum):
    """What to do when a configuration violates a constraint."""

    STRICT = "strict"
    """Report and refuse. Nothing is adjusted."""

    REPAIR = "repair"
    """Adjust what can be adjusted, report every change, refuse only if
    something unrepairable remains."""

    WARN = "warn"
    """Report everything and proceed regardless. An escape hatch for
    deliberately unusual experiments."""


@dataclass(frozen=True)
class Repair:
    """One adjustment the resolver made."""

    constraint: str
    field: str
    before: str
    after: str

    def as_dict(self) -> dict:
        """Plain data, ready to serialise."""
        return {
            "constraint": self.constraint,
            "field": self.field,
            "before": self.before,
            "after": self.after,
        }

    def describe(self) -> str:
        return f"{self.field}: {self.before} -> {self.after}  ({self.constraint})"


@dataclass
class ValidationReport:
    """The outcome of resolving one configuration."""

    settings: PipelineSettings
    issues: list[ValidationIssue] = field(default_factory=list)
    repairs: list[Repair] = field(default_factory=list)
    unresolved: list[ValidationIssue] = field(default_factory=list)
    exhausted_rounds: bool = False

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def ok(self) -> bool:
        """True when the run may proceed."""
        return not self.unresolved and not self.exhausted_rounds

    def as_dict(self) -> dict:
        """The whole outcome as plain data.

        ``render()`` is the same information written for a person; this is the
        same information written for a program.
        """
        return {
            "ok": self.ok,
            "exhausted_rounds": self.exhausted_rounds,
            "issues": [i.as_dict() for i in self.issues],
            "repairs": [r.as_dict() for r in self.repairs],
            "unresolved": [i.as_dict() for i in self.unresolved],
        }

    def render(self) -> str:
        """Human-readable summary, for logs and the pre-flight tool."""
        lines: list[str] = []
        if self.repairs:
            lines.append(f"Adjusted {len(self.repairs)} setting(s):")
            lines += [f"  {r.describe()}" for r in self.repairs]
        if self.warnings:
            lines.append(f"{len(self.warnings)} warning(s):")
            lines += [f"  {i.field}: {i.message}" for i in self.warnings]
        if self.unresolved:
            lines.append(f"{len(self.unresolved)} unresolved problem(s):")
            lines += [f"  {i.field}: {i.message}" for i in self.unresolved]
        if self.exhausted_rounds:
            lines.append(
                "Constraints could not be satisfied together: repairs kept "
                "undoing each other. The values above conflict."
            )
        if not lines:
            lines.append("Configuration OK.")
        return "\n".join(lines)


class ValidationError(RuntimeError):
    """Raised when a configuration cannot be made valid."""

    def __init__(self, report: ValidationReport) -> None:
        super().__init__("Configuration rejected:\n" + report.render())
        self.report = report


class Resolver:
    """Applies a set of constraints to a configuration."""

    def __init__(
        self,
        constraints: list[Constraint] | None = None,
        *,
        policy: Policy = Policy.REPAIR,
        max_rounds: int = DEFAULT_MAX_ROUNDS,
    ) -> None:
        if constraints is None:
            from app.validation.registry import all_constraints

            constraints = all_constraints()
        self.constraints = constraints
        self.policy = policy
        self.max_rounds = max_rounds

    # ── Main entry point ──────────────────────────────────────────────────────

    def resolve(self, settings: PipelineSettings) -> ValidationReport:
        """Check *settings*, repairing per policy, and return what happened.

        Never raises — the caller decides what to do with the report. An empty
        constraint set is a no-op that returns the settings unchanged.
        """
        ctx = ValidationContext.from_settings(settings)

        if self.policy in (Policy.STRICT, Policy.WARN):
            issues = self._check_all(ctx)
            unresolved = (
                [i for i in issues if i.severity == Severity.ERROR]
                if self.policy is Policy.STRICT
                else []
            )
            return ValidationReport(
                settings=ctx.settings, issues=issues, unresolved=unresolved
            )

        return self._repair_to_fixpoint(ctx)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _check_all(self, ctx: ValidationContext) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for constraint in self.constraints:
            issues.extend(constraint.check(ctx))
        return issues

    def _repair_to_fixpoint(self, ctx: ValidationContext) -> ValidationReport:
        repairs: list[Repair] = []
        exhausted = False

        for _ in range(self.max_rounds):
            progressed = False
            for constraint in self.constraints:
                found = constraint.check(ctx)
                if not found or not constraint.repairable:
                    continue
                repaired = constraint.repair(ctx)
                if repaired.settings == ctx.settings:
                    continue  # repair declined to change anything
                repairs.extend(self._diff(constraint, ctx, repaired))
                ctx = repaired
                progressed = True
            if not progressed:
                break
        else:
            # Loop ran the full count without settling: constraints conflict.
            exhausted = bool(self._check_all(ctx))

        issues = self._check_all(ctx)
        unresolved = [i for i in issues if i.severity == Severity.ERROR]
        return ValidationReport(
            settings=ctx.settings,
            issues=issues,
            repairs=repairs,
            unresolved=unresolved,
            exhausted_rounds=exhausted,
        )

    @staticmethod
    def _diff(
        constraint: Constraint,
        before: ValidationContext,
        after: ValidationContext,
    ) -> list[Repair]:
        """Describe what a repair changed, for the report."""
        import dataclasses

        changes: list[Repair] = []

        def walk(prefix: str, a, b) -> None:
            if a == b:
                return
            if dataclasses.is_dataclass(a) and dataclasses.is_dataclass(b):
                for f in dataclasses.fields(a):
                    walk(
                        f"{prefix}.{f.name}" if prefix else f.name,
                        getattr(a, f.name),
                        getattr(b, f.name),
                    )
                return
            changes.append(
                Repair(
                    constraint=constraint.NAME,
                    field=prefix,
                    before=f"{a:g}" if isinstance(a, (int, float)) else str(a),
                    after=f"{b:g}" if isinstance(b, (int, float)) else str(b),
                )
            )

        walk("", before.settings, after.settings)
        return changes


def resolve_or_raise(
    settings: PipelineSettings,
    *,
    policy: Policy = Policy.REPAIR,
    constraints: list[Constraint] | None = None,
    verbose: bool = True,
) -> PipelineSettings:
    """Validate *settings*, returning the settings a run should actually use.

    Raises ``ValidationError`` when the configuration cannot be made valid.
    This is the function both call sites use — the pre-flight tool and the
    render entrypoint — so they cannot drift apart.
    """
    resolver = Resolver(constraints, policy=policy)
    report = resolver.resolve(settings)
    if verbose:
        summary = report.render()
        if summary != "Configuration OK.":
            print(summary)
    if not report.ok:
        raise ValidationError(report)
    return report.settings
