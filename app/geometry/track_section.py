"""Modular track section with rails, sleepers, and fasteners."""

from __future__ import annotations

from typing import List

import bpy

from app.geometry.layout import TrackSectionLayout
from app.geometry.utils import move_to_collection, parent_object, replace_material


class TrackSection:
    """
    Represents a single modular section of railway track.

    Creates an H-shaped assembly (top view: -- : | : --):
      - Two parallel rails
      - Three-piece sleeper (left outer, middle, right outer)
      - Eight fastener cylinders distributed across the sleeper pieces
    """

    SECTION_PARENT_ROLE = "section_parent"
    LEFT_RAIL_ROLE = "left_rail"
    RIGHT_RAIL_ROLE = "right_rail"
    SLEEPER_ROLE = "sleeper"
    FASTENER_ROLE = "fastener"

    def __init__(
        self,
        rail_material=None,
        sleeper_material=None,
        fastener_material=None,
        length: float = 0.15,
        rail_spacing: float = 1.4,
        rail_height: float = 0.16,
        rail_width: float = 0.06,
        sleeper_height: float = 0.12,
        rail_lift: float = 0.0,
        rail_length: float | None = None,
        sleeper_length_ratio: float = 0.72,
    ):
        self.rail_material = rail_material
        self.sleeper_material = sleeper_material
        self.fastener_material = fastener_material

        self.length = length
        self.rail_spacing = rail_spacing
        self.rail_height = rail_height
        self.rail_width = rail_width
        self.sleeper_height = sleeper_height
        self.rail_lift = rail_lift
        self.rail_length = rail_length if rail_length is not None else length

        self.screw_radius = 0.015
        self.screw_length = 0.05
        self.sleeper_length_ratio = sleeper_length_ratio

        self.left_rail = None
        self.right_rail = None
        self.left_sleeper = None
        self.middle_sleeper = None
        self.right_sleeper = None
        self.sleeper = None
        self.fasteners: List[object] = []
        self.section_parent = None

    def build(self, location=(0, 0, 0), *, target_collection=None, parent=None) -> object:
        x, y, z = location
        target_collection = target_collection or bpy.context.scene.collection

        bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
        self.section_parent = bpy.context.active_object
        self.section_parent.name = "TrackSection"
        self._register(self.section_parent, role=self.SECTION_PARENT_ROLE, collection=target_collection)
        if parent is not None:
            parent_object(self.section_parent, parent)

        layout = self._compute_layout(x)

        self.left_sleeper = self._create_sleeper_piece(
            x_pos=layout.left_sleeper_x,
            width=layout.side_sleeper_width,
            parent_location=(x, y, z),
            collection=target_collection,
            name="SleeperLeft",
        )
        self.left_rail = self._create_rail(
            x_offset=layout.left_rail_x - x,
            parent_location=(x, y, z),
            role=self.LEFT_RAIL_ROLE,
            collection=target_collection,
        )
        self.middle_sleeper = self._create_sleeper_piece(
            x_pos=layout.middle_sleeper_x,
            width=layout.middle_sleeper_width,
            parent_location=(x, y, z),
            collection=target_collection,
            name="SleeperMiddle",
        )
        self.right_rail = self._create_rail(
            x_offset=layout.right_rail_x - x,
            parent_location=(x, y, z),
            role=self.RIGHT_RAIL_ROLE,
            collection=target_collection,
        )
        self.right_sleeper = self._create_sleeper_piece(
            x_pos=layout.right_sleeper_x,
            width=layout.side_sleeper_width,
            parent_location=(x, y, z),
            collection=target_collection,
            name="SleeperRight",
        )
        self.sleeper = self.middle_sleeper
        self.fasteners = self._create_fasteners(parent_location=(x, y, z), collection=target_collection)
        return self.section_parent

    # ------------------------------------------------------------------
    # Component builders
    # ------------------------------------------------------------------

    def _create_rail(self, x_offset, parent_location, *, role, collection) -> object:
        x, y, z = parent_location
        bpy.ops.mesh.primitive_cube_add(size=1)
        rail = bpy.context.active_object
        rail.name = "RailPiece"
        rail.scale = (self.rail_width, self.rail_length, self.rail_height)
        rail.location = (x + x_offset, y, self._rail_center_z(z))
        self._register(rail, role=role, collection=collection,
                       parent=self.section_parent, material=self.rail_material)
        return rail

    def _create_sleeper_piece(self, *, x_pos, width, parent_location, collection, name) -> object:
        _, y, z = parent_location
        bpy.ops.mesh.primitive_cube_add(size=1)
        sleeper = bpy.context.active_object
        sleeper.name = name
        sleeper.scale = (width, self.length * self.sleeper_length_ratio, self.sleeper_height)
        sleeper.location = (x_pos, y, self._sleeper_center_z(z))
        self._register(sleeper, role=self.SLEEPER_ROLE, collection=collection,
                       parent=self.section_parent, material=self.sleeper_material)
        return sleeper

    def _create_fasteners(self, parent_location, *, collection) -> List[object]:
        x, y, z = parent_location
        layout = self._compute_layout(x)

        x_inset = max(self.screw_radius * 1.4, 0.01)
        outer_ratio = 0.65
        sw, mw = layout.side_sleeper_width, layout.middle_sleeper_width
        pair_x_positions = [
            layout.left_sleeper_x  - sw / 2 + sw * outer_ratio,
            layout.middle_sleeper_x - mw / 2 + x_inset,
            layout.middle_sleeper_x + mw / 2 - x_inset,
            layout.right_sleeper_x  + sw / 2 - sw * outer_ratio,
        ]
        pair_offset_y = max((self.length * self.sleeper_length_ratio) * 0.24, 0.02)
        screw_z = self._sleeper_top_z(z) + self.screw_length / 2

        return [
            self._create_screw(px, sy, screw_z, collection=collection)
            for px in pair_x_positions
            for sy in (y - pair_offset_y, y + pair_offset_y)
        ]

    def _create_screw(self, x, y, z, *, collection) -> object:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=self.screw_radius, depth=self.screw_length, location=(x, y, z)
        )
        screw = bpy.context.active_object
        screw.name = "Fastener"
        self._register(screw, role=self.FASTENER_ROLE, collection=collection,
                       parent=self.section_parent, material=self.fastener_material)
        return screw

    # ------------------------------------------------------------------
    # Layout computation
    # ------------------------------------------------------------------

    def _compute_layout(self, center_x: float) -> TrackSectionLayout:
        left_rail_x  = center_x - self.rail_spacing / 2
        right_rail_x = center_x + self.rail_spacing / 2

        side_sleeper_width = max(self.rail_width * 1.2, 0.08) * 2

        middle_edge_left  = left_rail_x  + self.rail_width / 2
        middle_edge_right = right_rail_x - self.rail_width / 2
        middle_sleeper_width = max(middle_edge_right - middle_edge_left, self.rail_width)
        middle_sleeper_x = (middle_edge_left + middle_edge_right) / 2

        left_sleeper_x  = left_rail_x  - self.rail_width / 2 - side_sleeper_width / 2
        right_sleeper_x = right_rail_x + self.rail_width / 2 + side_sleeper_width / 2

        return TrackSectionLayout(
            left_sleeper_x=left_sleeper_x,
            left_rail_x=left_rail_x,
            middle_sleeper_x=middle_sleeper_x,
            middle_sleeper_width=middle_sleeper_width,
            right_rail_x=right_rail_x,
            right_sleeper_x=right_sleeper_x,
            side_sleeper_width=side_sleeper_width,
        )

    # ------------------------------------------------------------------
    # Geometry serialisation
    # ------------------------------------------------------------------

    def geometry_payload(self) -> dict[str, float]:
        return {
            "length": self.length,
            "rail_spacing": self.rail_spacing,
            "rail_height": self.rail_height,
            "rail_width": self.rail_width,
            "sleeper_height": self.sleeper_height,
            "rail_lift": self.rail_lift,
            "rail_length": self.rail_length,
            "sleeper_length_ratio": self.sleeper_length_ratio,
            "screw_radius": self.screw_radius,
            "screw_length": self.screw_length,
        }

    # ------------------------------------------------------------------
    # Z-axis helpers
    # ------------------------------------------------------------------

    def _sleeper_center_z(self, base_z: float) -> float:
        return base_z + self.sleeper_height / 2

    def _sleeper_top_z(self, base_z: float) -> float:
        return self._sleeper_center_z(base_z) + self.sleeper_height / 2

    def _rail_center_z(self, base_z: float) -> float:
        return self._sleeper_top_z(base_z) + self.rail_height / 2 + self.rail_lift - self._rail_drop()

    def _rail_drop(self) -> float:
        """Lower rails slightly so fasteners remain visible in render."""
        return min(
            max(self.screw_radius, 0.4 * self.screw_length),
            0.25 * self.rail_height,
            0.25 * self.sleeper_height,
        )

    # ------------------------------------------------------------------
    # Material application (for cached collection instances)
    # ------------------------------------------------------------------

    @classmethod
    def apply_materials_to_collection(
        cls,
        collection,
        *,
        rail_material=None,
        sleeper_material=None,
        fastener_material=None,
    ) -> None:
        for obj in collection.objects:
            role = obj.get("track_section_role")
            if role in {cls.LEFT_RAIL_ROLE, cls.RIGHT_RAIL_ROLE}:
                replace_material(obj, rail_material)
            elif role == cls.SLEEPER_ROLE:
                replace_material(obj, sleeper_material)
            elif role == cls.FASTENER_ROLE:
                replace_material(obj, fastener_material)

    # ------------------------------------------------------------------
    # Internal object registration
    # ------------------------------------------------------------------

    def _register(self, obj, *, role, collection, parent=None, material=None) -> None:
        obj["track_section_role"] = role
        move_to_collection(obj, collection)
        if parent is not None:
            parent_object(obj, parent)
        replace_material(obj, material)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_all_components(self) -> List[object]:
        candidates = [
            self.left_rail,
            self.right_rail,
            self.left_sleeper,
            self.middle_sleeper,
            self.right_sleeper,
        ]
        return [c for c in candidates if c is not None] + list(self.fasteners)

    def get_sleeper(self) -> object:
        return self.sleeper

    def get_rails(self) -> tuple:
        return self.left_rail, self.right_rail
