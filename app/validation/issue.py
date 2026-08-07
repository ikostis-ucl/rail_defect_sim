"""What a constraint reports when it is unhappy.

``ValidationIssue`` is deliberately the type ``TrackGeometryConfig.validate()``
already returns, rather than a parallel vocabulary — the existing geometry
checks migrate into constraints without changing what they emit.
"""

from __future__ import annotations

from enum import StrEnum

# Re-exported: the canonical definition stays with the geometry config that has
# always produced it. Constraints and the resolver import it from here so that
# the whole validation layer has one obvious source.
from app.config.geometry import ValidationIssue

__all__ = ["Severity", "ValidationIssue", "error", "warning"]


class Severity(StrEnum):
    """How seriously to take an issue.

    ``ERROR``   — the configuration is impossible or would produce a useless
                  render; the resolver repairs or rejects it.
    ``WARNING`` — unusual but renderable; reported and otherwise left alone.
    """

    ERROR = "error"
    WARNING = "warning"


def error(field: str, message: str) -> ValidationIssue:
    return ValidationIssue(Severity.ERROR, field, message)


def warning(field: str, message: str) -> ValidationIssue:
    return ValidationIssue(Severity.WARNING, field, message)
