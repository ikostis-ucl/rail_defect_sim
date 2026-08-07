"""The set of constraints the resolver runs.

Adding a rule means adding one entry here — the same pattern as ``ALL_DEFECTS``
in the defect registry, so there is one obvious place to look and one line to
change.

Still to come: sleeper spacing, the camera datum, camera field of view, defect
observability, render budget.
"""

from __future__ import annotations

from app.validation.constraint import Constraint
from app.validation.constraints.geometry import GEOMETRY_CONSTRAINTS

#: Constraint classes, instantiated fresh by ``all_constraints()``.
CONSTRAINT_TYPES: list[type[Constraint]] = [
    *GEOMETRY_CONSTRAINTS,
]


def all_constraints() -> list[Constraint]:
    """Instantiate every registered constraint."""
    return [constraint_type() for constraint_type in CONSTRAINT_TYPES]
