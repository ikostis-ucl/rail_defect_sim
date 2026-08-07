"""Everything a constraint is allowed to look at, in one object.

Before this existed, a rule spanning camera and track geometry could not be
written at all: the two configs never met anywhere in the codebase. The context
puts settings, geometry, the active rail profile and the derived cross-config
quantities side by side, so a constraint reads one object and a repair returns
a new one.

The context is immutable. Repairs return a *modified copy* via the ``with_*``
helpers, which keeps the original configuration intact for reporting what was
changed and why.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from app.config import PipelineSettings
from app.config.profiles import PROFILES, RailProfileSpec


@dataclass(frozen=True)
class ValidationContext:
    """One complete, self-consistent description of a run under inspection."""

    settings: PipelineSettings

    # ── Config views ──────────────────────────────────────────────────────────

    @property
    def geometry(self):
        return self.settings.geometry

    @property
    def camera(self):
        return self.settings.camera

    @property
    def render(self):
        return self.settings.render

    @property
    def environment(self):
        return self.settings.environment

    @property
    def profile(self) -> RailProfileSpec | None:
        """The standard this geometry claims to follow, if it is a known one.

        ``None`` when the named profile is not in the catalog — in that case no
        standard is on record, so profile-based checks stand down rather than
        inventing one.
        """
        return PROFILES.get(self.geometry.profile)

    # ── Modified copies ───────────────────────────────────────────────────────

    def with_settings(self, **changes) -> "ValidationContext":
        return ValidationContext(dataclasses.replace(self.settings, **changes))

    def with_geometry(self, **changes) -> "ValidationContext":
        return self.with_settings(
            geometry=dataclasses.replace(self.settings.geometry, **changes)
        )

    def with_camera(self, **changes) -> "ValidationContext":
        return self.with_settings(
            camera=dataclasses.replace(self.settings.camera, **changes)
        )

    def with_render(self, **changes) -> "ValidationContext":
        return self.with_settings(
            render=dataclasses.replace(self.settings.render, **changes)
        )

    def with_left_rail(self, **changes) -> "ValidationContext":
        return self.with_geometry(
            left_rail=dataclasses.replace(self.settings.geometry.left_rail, **changes)
        )

    def with_right_rail(self, **changes) -> "ValidationContext":
        return self.with_geometry(
            right_rail=dataclasses.replace(self.settings.geometry.right_rail, **changes)
        )

    # ── Construction ──────────────────────────────────────────────────────────

    @classmethod
    def from_settings(cls, settings: PipelineSettings) -> "ValidationContext":
        return cls(settings=settings)
