"""Pre-render configuration validation.

Checks a run *before* Blender is launched, so an impossible or useless
configuration is caught in milliseconds rather than after a build. Nothing here
imports ``bpy``; ``tests/test_bpy_free_imports.py`` enforces that.

The pieces:

    ValidationContext  every config a rule may look at, in one object
    derived            quantities that only exist across two configs
    Constraint         one rule: check, and how to repair it
    Resolver           run them all, repair to a fixpoint, report
    registry           the set of rules in force

Typical use::

    from app.validation import resolve_or_raise
    settings = resolve_or_raise(settings)
"""

from app.validation.constraint import Constraint, Interval, IntervalConstraint
from app.validation.context import ValidationContext
from app.validation.issue import Severity, ValidationIssue, error, warning
from app.validation.registry import CONSTRAINT_TYPES, all_constraints
from app.validation.resolver import (
    Policy,
    Repair,
    Resolver,
    ValidationError,
    ValidationReport,
    resolve_or_raise,
)

__all__ = [
    "ValidationContext",
    "Constraint",
    "IntervalConstraint",
    "Interval",
    "ValidationIssue",
    "Severity",
    "error",
    "warning",
    "Resolver",
    "Policy",
    "Repair",
    "ValidationReport",
    "ValidationError",
    "resolve_or_raise",
    "all_constraints",
    "CONSTRAINT_TYPES",
]
