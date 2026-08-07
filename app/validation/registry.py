"""The set of constraints the resolver runs.

Adding a rule means adding one entry here — the same pattern as ``ALL_DEFECTS``
in the defect registry, so there is one obvious place to look and one line to
change.

Deliberately empty for now: this is the foundation only. The actual rules land
as their own pieces of work — the existing geometry checks, sleeper spacing,
the camera datum, camera field of view, defect observability, render budget.
An empty registry makes the resolver a no-op, which is exactly what should
happen before any rule exists.
"""

from __future__ import annotations

from app.validation.constraint import Constraint

#: Constraint classes, instantiated fresh by ``all_constraints()``.
CONSTRAINT_TYPES: list[type[Constraint]] = []


def all_constraints() -> list[Constraint]:
    """Instantiate every registered constraint."""
    return [constraint_type() for constraint_type in CONSTRAINT_TYPES]
