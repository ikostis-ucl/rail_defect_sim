"""What a constraint reports when it is unhappy.

``ValidationIssue`` is defined here, in the layer that produces it. It used to
live in ``app/config/geometry.py`` for the historical reason that
``TrackGeometryConfig.validate()`` was the only thing that emitted one. Now that
every constraint does, a validation type living inside a config module inverted
the layering: validation reads config, never the other way round.

``geometry.py`` still returns these from ``validate()``, but imports the type
only under ``TYPE_CHECKING``, so the runtime dependency stays one-way.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["Severity", "ValidationIssue", "error", "warning"]


class Severity(StrEnum):
    """How seriously to take an issue.

    ``ERROR``   — the configuration is impossible or would produce a useless
                  render; the resolver repairs or rejects it.
    ``WARNING`` — unusual but renderable; reported and otherwise left alone.
    """

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """One problem found in a configuration.

    ``message`` is for a person. Everything else is for a program, so that a
    caller can act on *which* problem this is and *what* the numbers were
    without reading English.

    ``code`` is the stable identifier — the ``NAME`` of the constraint that
    raised it. It plays the same role an exception type does: you match on
    ``code == "rails_overlap"`` rather than searching the message for a phrase,
    so rewording the message never breaks a caller. Codes are therefore a
    promise: renaming one is a breaking change.

    The numeric fields are optional because not every rule is about a quantity
    in a range. When they are present, a caller can show the offending value
    against its allowed bounds without parsing the sentence.
    """

    severity: str   # Severity.ERROR | Severity.WARNING
    field: str      # which config field is implicated
    message: str    # human-readable description

    code: str = ""                      # constraint NAME; stable across rewording
    value: float | None = None          # the offending quantity
    expected_min: float | None = None   # lower bound, if the rule has one
    expected_max: float | None = None   # upper bound, if the rule has one
    unit: str = ""                      # unit of value and the bounds

    def as_dict(self) -> dict:
        """Plain data, ready to serialise."""
        return {
            "code": self.code,
            "severity": str(self.severity),
            "field": self.field,
            "message": self.message,
            "value": self.value,
            "expected_min": self.expected_min,
            "expected_max": self.expected_max,
            "unit": self.unit,
        }


def error(field: str, message: str, code: str = "", **data) -> ValidationIssue:
    return ValidationIssue(Severity.ERROR, field, message, code=code, **data)


def warning(field: str, message: str, code: str = "", **data) -> ValidationIssue:
    return ValidationIssue(Severity.WARNING, field, message, code=code, **data)
