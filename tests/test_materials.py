"""
Tests for material class metadata and structure.
Actual node-graph calls go to the bpy MagicMock stub.
"""
import pytest

from app.config import AppearanceConfig, NoiseSurfaceAppearance, SurfaceAppearance
from app.materials.base import Material, NoiseBlendMaterial, PrincipledMaterial
from app.materials.clip import ClipMaterial
from app.materials.factory import MaterialFactory
from app.materials.fastener import FastenerMaterial
from app.materials.grass import GrassMaterial
from app.materials.rail import RailMaterial
from app.materials.sleeper import SleeperMaterial

ALL_MATERIALS = [RailMaterial, SleeperMaterial, GrassMaterial, ClipMaterial, FastenerMaterial]

# Each material paired with an appearance of the shape it expects.
APPEARANCE_FOR = {
    RailMaterial: SurfaceAppearance(),
    SleeperMaterial: SurfaceAppearance(),
    ClipMaterial: SurfaceAppearance(),
    FastenerMaterial: SurfaceAppearance(),
    GrassMaterial: NoiseSurfaceAppearance(),
}


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_has_name(cls):
    assert hasattr(cls, "NAME")
    assert isinstance(cls.NAME, str)
    assert cls.NAME != ""


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_is_material_subclass(cls):
    assert issubclass(cls, Material)


def test_names_are_unique():
    names = [c.NAME for c in ALL_MATERIALS]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_create_calls_bpy_materials_new(cls):
    import bpy
    bpy.data.materials.new.reset_mock()
    cls.create(APPEARANCE_FOR[cls])
    bpy.data.materials.new.assert_called_once_with(name=cls.NAME)


def test_material_base_is_abstract():
    """Material cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Material()  # type: ignore[abstract]


def test_sleeper_material_name_not_ballast():
    assert "allast" not in SleeperMaterial.NAME


def test_no_ballast_material_class():
    import app.materials as mat_package
    assert not hasattr(mat_package, "BallastMaterial")


# ── Appearance-driven construction ────────────────────────────────────────────

def test_uniform_surfaces_share_one_implementation():
    """Rail/sleeper/fastener/clip differ only by appearance, not by node code."""
    for cls in (RailMaterial, SleeperMaterial, FastenerMaterial, ClipMaterial):
        assert issubclass(cls, PrincipledMaterial)
    assert issubclass(GrassMaterial, NoiseBlendMaterial)


def test_principled_material_reads_every_appearance_field():
    """Base colour, metallic and roughness all reach the shader node."""
    from unittest.mock import MagicMock

    nodes, links = MagicMock(), MagicMock()
    created = {}

    class _Sockets(dict):
        """Blender node inputs: any socket name resolves to a socket object."""

        def __missing__(self, key):
            self[key] = MagicMock()
            return self[key]

    def _new(type):
        node = MagicMock()
        node.inputs = _Sockets()
        created[type] = node
        return node

    nodes.new.side_effect = _new
    appearance = SurfaceAppearance(base_color=(0.1, 0.2, 0.3, 1.0), metallic=0.75, roughness=0.25)
    PrincipledMaterial._build_nodes(nodes, links, appearance)

    principled = created["ShaderNodeBsdfPrincipled"]
    assert principled.inputs["Base Color"].default_value == (0.1, 0.2, 0.3, 1.0)
    assert principled.inputs["Metallic"].default_value == 0.75
    assert principled.inputs["Roughness"].default_value == 0.25


def test_factory_uses_configured_appearance():
    """MaterialFactory passes each surface its own appearance, not a default."""
    custom = SurfaceAppearance(base_color=(1.0, 0.0, 0.0, 1.0), metallic=0.1, roughness=0.9)
    factory = MaterialFactory(AppearanceConfig(rail=custom))
    assert factory.appearance.rail is custom
    # Untouched surfaces keep their defaults.
    assert factory.appearance.sleeper.roughness == AppearanceConfig().sleeper.roughness


def test_factory_defaults_when_no_appearance_given():
    factory = MaterialFactory()
    assert isinstance(factory.appearance, AppearanceConfig)
