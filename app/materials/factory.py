from app.materials.rail import RailMaterial
from app.materials.sleeper import SleeperMaterial
from app.materials.grass import GrassMaterial
from app.materials.clip import ClipMaterial
from app.materials.fastener import FastenerMaterial


class MaterialFactory:
    """Delegates material creation to the typed material classes."""

    def create_rail_material(self):     return RailMaterial.create()
    def create_sleeper_material(self):  return SleeperMaterial.create()
    def create_grass_material(self):    return GrassMaterial.create()
    def create_clip_material(self):     return ClipMaterial.create()
    def create_fastener_material(self): return FastenerMaterial.create()
