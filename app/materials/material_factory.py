# Back-compat shim. Canonical locations: app/materials/base.py, rail.py, etc.
from app.materials.base import Material, NoiseBlendMaterial, PrincipledMaterial
from app.materials.clip import ClipMaterial
from app.materials.factory import MaterialFactory
from app.materials.fastener import FastenerMaterial
from app.materials.grass import GrassMaterial
from app.materials.rail import RailMaterial
from app.materials.sleeper import SleeperMaterial

__all__ = [
    "Material", "PrincipledMaterial", "NoiseBlendMaterial",
    "RailMaterial", "SleeperMaterial",
    "GrassMaterial", "ClipMaterial", "FastenerMaterial",
    "MaterialFactory",
]
