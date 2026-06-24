"""Procedural materials for the railway scene."""

from __future__ import annotations

from abc import ABC, abstractmethod

import bpy


# ---------------------------------------------------------------------------
# Material base class
# ---------------------------------------------------------------------------


class Material(ABC):
    """Abstract base for all procedural scene materials."""

    NAME: str

    @classmethod
    def create(cls) -> bpy.types.Material:
        mat = bpy.data.materials.new(name=cls.NAME)
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        cls._build_nodes(mat.node_tree.nodes, mat.node_tree.links)
        return mat

    @classmethod
    @abstractmethod
    def _build_nodes(cls, nodes, links) -> None:
        """Build the complete material node graph."""


# ---------------------------------------------------------------------------
# Concrete material implementations
# ---------------------------------------------------------------------------


class RailMaterial(Material):
    NAME = "Rail_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.62, 0.64, 0.66, 1.0)
        principled.inputs["Metallic"].default_value = 0.9
        principled.inputs["Roughness"].default_value = 0.35
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


class SleeperMaterial(Material):
    NAME = "Sleeper_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.inputs["Roughness"].default_value = 0.8

        noise = nodes.new(type="ShaderNodeTexNoise")
        noise.noise_dimensions = "3D"
        if hasattr(noise, "noise_type"):
            noise.noise_type = "FBM"
        noise.inputs["Scale"].default_value = 20.0

        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        color_ramp.color_ramp.elements[0].color = (0.02, 0.01, 0.0, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.05, 0.03, 0.02, 1.0)

        links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


class BallastMaterial(Material):
    NAME = "Ballast_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.26, 0.16, 0.09, 1.0)
        principled.inputs["Roughness"].default_value = 0.85
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


class GrassMaterial(Material):
    NAME = "Grass_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"

        noise = nodes.new(type="ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 20.0

        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        color_ramp.color_ramp.elements[0].color = (0.01, 0.02, 0.0, 1.0)
        color_ramp.color_ramp.elements[1].color = (0.02, 0.05, 0.01, 1.0)

        links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


class ClipMaterial(Material):
    NAME = "Clip_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        principled.inputs["Metallic"].default_value = 0.9
        principled.inputs["Roughness"].default_value = 0.35
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


class FastenerMaterial(Material):
    NAME = "Fastener_Material"

    @classmethod
    def _build_nodes(cls, nodes, links) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1.0)
        principled.inputs["Metallic"].default_value = 0.15
        principled.inputs["Roughness"].default_value = 0.7
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


# ---------------------------------------------------------------------------
# MaterialFactory — thin coordinator
# ---------------------------------------------------------------------------


class MaterialFactory:
    """Delegates material creation to the typed material classes."""

    def create_rail_material(self):     return RailMaterial.create()
    def create_sleeper_material(self):  return SleeperMaterial.create()
    def create_ballast_material(self):  return BallastMaterial.create()
    def create_grass_material(self):    return GrassMaterial.create()
    def create_clip_material(self):     return ClipMaterial.create()
    def create_fastener_material(self): return FastenerMaterial.create()
