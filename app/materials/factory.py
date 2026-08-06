from app.config import AppearanceConfig
from app.materials.clip import ClipMaterial
from app.materials.fastener import FastenerMaterial
from app.materials.grass import GrassMaterial
from app.materials.rail import RailMaterial
from app.materials.sleeper import SleeperMaterial


class MaterialFactory:
    """Builds each scene material from its appearance description.

    Pairs a material *type* (which knows how to build node graphs) with an
    *appearance* (which says what it should look like). Adding a surface means
    adding a field to AppearanceConfig and one line here.
    """

    def __init__(self, appearance: AppearanceConfig | None = None) -> None:
        self.appearance = appearance if appearance is not None else AppearanceConfig()

    def create_rail_material(self):
        return RailMaterial.create(self.appearance.rail)

    def create_sleeper_material(self):
        return SleeperMaterial.create(self.appearance.sleeper)

    def create_fastener_material(self):
        return FastenerMaterial.create(self.appearance.fastener)

    def create_clip_material(self):
        return ClipMaterial.create(self.appearance.clip)

    def create_grass_material(self):
        return GrassMaterial.create(self.appearance.grass)
