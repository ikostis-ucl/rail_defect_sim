"""
Tests for material class metadata and structure.
Actual node-graph calls go to the bpy MagicMock stub.
"""
import pytest
from app.materials.base import Material
from app.materials.rail import RailMaterial
from app.materials.sleeper import SleeperMaterial
from app.materials.grass import GrassMaterial
from app.materials.clip import ClipMaterial
from app.materials.fastener import FastenerMaterial

ALL_MATERIALS = [RailMaterial, SleeperMaterial, GrassMaterial, ClipMaterial, FastenerMaterial]


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_has_name(cls):
    assert hasattr(cls, "NAME")
    assert isinstance(cls.NAME, str)
    assert cls.NAME != ""


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_is_material_subclass(cls):
    assert issubclass(cls, Material)


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_names_are_unique(cls):
    names = [c.NAME for c in ALL_MATERIALS]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("cls", ALL_MATERIALS)
def test_create_calls_bpy_materials_new(cls):
    import bpy
    bpy.data.materials.new.reset_mock()
    cls.create()
    bpy.data.materials.new.assert_called_once_with(name=cls.NAME)


def test_material_base_is_abstract():
    """Material cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Material()  # type: ignore[abstract]


def test_sleeper_material_name_not_ballast():
    assert "allast" not in SleeperMaterial.NAME


def test_no_ballast_material_class():
    import app.materials as mat_package
    import inspect, importlib, pkgutil
    # Ensure BallastMaterial is not exported from the materials package
    assert not hasattr(mat_package, "BallastMaterial")
