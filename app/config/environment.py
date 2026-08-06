"""
Environment configuration — everything around the track rather than the track.

The *data* half of the scene: world background, lighting, and the ground plane.
The *builder* halves are ``app.scene.SceneSetup`` (world and lighting) and
``app.geometry.TrackBuilder`` (ground plane). Nothing here imports ``bpy``.

Colours are linear RGBA tuples in 0..1. Distances are in metres.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config.types import RGBA


@dataclass(frozen=True)
class WorldConfig:
    """Scene world / background shader."""

    # Near-black warm brown: keeps the horizon from reading as a bright band
    # while leaving the track the brightest thing in frame.
    background_color: RGBA = (0.01, 0.005, 0.002, 1.0)


@dataclass(frozen=True)
class SunConfig:
    """Single directional sun lamp."""

    energy: float = 5.0
    location: tuple = (5.0, 5.0, 10.0)
    # Shadows off by default: flatter, more legible renders for geometry
    # inspection, and cheaper in EEVEE.
    cast_shadows: bool = False


@dataclass(frozen=True)
class GroundConfig:
    """Ground plane beneath and beside the track."""

    half_width: float = 100.0   # X extent either side of the track centreline

    # Height *relative to the track base elevation*, so the ground follows the
    # track when base_elevation changes instead of drifting apart from it.
    # Default -0.4 places the ground at world Z = -0.3 with the default
    # base_elevation of 0.1, matching the ballast shoulder it stands in for.
    z_offset: float = -0.4


@dataclass(frozen=True)
class EnvironmentConfig:
    """Everything in the scene that is not track geometry."""

    world: WorldConfig = field(default_factory=WorldConfig)
    sun: SunConfig = field(default_factory=SunConfig)
    ground: GroundConfig = field(default_factory=GroundConfig)
