"""
Surface appearance configuration — how each component looks.

The *data* half of materials. The *builder* half is ``app.materials``, which
turns these descriptions into Blender shader node graphs. Nothing here imports
``bpy``.

Today every surface is a plain Principled BSDF driven by three scalars. The
project intends to replace these with PBR texture maps extracted from real
photographs, so ``SurfaceAppearance`` is deliberately a *description of a
surface* rather than a set of BSDF arguments: adding ``albedo_map``,
``roughness_map`` and ``normal_map`` fields later extends this type instead of
replacing it.

Colours are linear RGBA tuples in 0..1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RGBA = tuple


@dataclass(frozen=True)
class SurfaceAppearance:
    """A uniform surface: base colour plus the two standard PBR scalars."""

    base_color: RGBA = (0.5, 0.5, 0.5, 1.0)
    metallic: float = 0.0
    roughness: float = 0.5


@dataclass(frozen=True)
class NoiseSurfaceAppearance:
    """A surface whose base colour is a procedural noise blend of two colours.

    Used for ground cover, where a flat colour reads as obviously synthetic.
    """

    color_low: RGBA = (0.01, 0.02, 0.0, 1.0)
    color_high: RGBA = (0.02, 0.05, 0.01, 1.0)
    noise_scale: float = 20.0
    metallic: float = 0.0
    roughness: float = 0.5


def _rail() -> SurfaceAppearance:
    # Worn steel: bright, strongly metallic, moderately polished by wheel contact.
    return SurfaceAppearance(base_color=(0.62, 0.64, 0.66, 1.0), metallic=0.9, roughness=0.35)


def _sleeper() -> SurfaceAppearance:
    # Weathered creosote-brown timber/concrete: non-metallic and very rough.
    return SurfaceAppearance(base_color=(0.26, 0.16, 0.09, 1.0), metallic=0.0, roughness=0.85)


def _fastener() -> SurfaceAppearance:
    # Dark oxidised iron: near-black, mostly non-metallic once corroded.
    return SurfaceAppearance(base_color=(0.02, 0.02, 0.02, 1.0), metallic=0.15, roughness=0.7)


def _clip() -> SurfaceAppearance:
    # Spring steel clip: same near-black tone but still bright metal.
    return SurfaceAppearance(base_color=(0.02, 0.02, 0.02, 1.0), metallic=0.9, roughness=0.35)


def _grass() -> NoiseSurfaceAppearance:
    return NoiseSurfaceAppearance()


@dataclass(frozen=True)
class AppearanceConfig:
    """Appearance for every surface in the scene."""

    rail: SurfaceAppearance = field(default_factory=_rail)
    sleeper: SurfaceAppearance = field(default_factory=_sleeper)
    fastener: SurfaceAppearance = field(default_factory=_fastener)
    clip: SurfaceAppearance = field(default_factory=_clip)
    grass: NoiseSurfaceAppearance = field(default_factory=_grass)
