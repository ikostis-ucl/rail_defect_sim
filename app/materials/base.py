"""Material builders — turn appearance descriptions into Blender node graphs.

The *builder* half of surfaces. The *data* half is
``app.config.appearance``, which is ``bpy``-free.

Two shared implementations cover every surface in the scene, so a new surface
usually means declaring a ``NAME`` and an appearance rather than writing node
code:

    PrincipledMaterial  — uniform surface from a SurfaceAppearance
    NoiseBlendMaterial  — two colours blended by procedural noise
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import bpy


class Material(ABC):
    """Abstract base for all procedural scene materials."""

    NAME: str

    @classmethod
    def create(cls, appearance) -> "bpy.types.Material":
        mat = bpy.data.materials.new(name=cls.NAME)
        mat.use_nodes = True
        mat.node_tree.nodes.clear()
        cls._build_nodes(mat.node_tree.nodes, mat.node_tree.links, appearance)
        return mat

    @classmethod
    @abstractmethod
    def _build_nodes(cls, nodes, links, appearance) -> None:
        """Build the complete material node graph from *appearance*."""


class PrincipledMaterial(Material):
    """A uniform surface: one Principled BSDF driven by three scalars."""

    @classmethod
    def _build_nodes(cls, nodes, links, appearance) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Base Color"].default_value = appearance.base_color
        principled.inputs["Metallic"].default_value = appearance.metallic
        principled.inputs["Roughness"].default_value = appearance.roughness
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])


class NoiseBlendMaterial(Material):
    """A surface whose base colour is a noise blend between two colours."""

    @classmethod
    def _build_nodes(cls, nodes, links, appearance) -> None:
        output = nodes.new(type="ShaderNodeOutputMaterial")
        principled = nodes.new(type="ShaderNodeBsdfPrincipled")
        principled.name = "Principled BSDF"
        principled.inputs["Metallic"].default_value = appearance.metallic
        principled.inputs["Roughness"].default_value = appearance.roughness

        noise = nodes.new(type="ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = appearance.noise_scale

        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        color_ramp.color_ramp.elements[0].color = appearance.color_low
        color_ramp.color_ramp.elements[1].color = appearance.color_high

        links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])
        links.new(principled.outputs["BSDF"], output.inputs["Surface"])
