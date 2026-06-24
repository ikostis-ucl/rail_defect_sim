from __future__ import annotations

from abc import ABC, abstractmethod

import bpy


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
