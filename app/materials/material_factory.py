# Canonical locations: app/materials/base.py, rail.py, sleeper.py, etc.
from app.materials.base import Material
from app.materials.rail import RailMaterial
from app.materials.sleeper import SleeperMaterial
from app.materials.grass import GrassMaterial
from app.materials.clip import ClipMaterial
from app.materials.fastener import FastenerMaterial
from app.materials.factory import MaterialFactory

__all__ = [
    "Material",
    "RailMaterial", "SleeperMaterial",
    "GrassMaterial", "ClipMaterial", "FastenerMaterial",
    "MaterialFactory",
]
