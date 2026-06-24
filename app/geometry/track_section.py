"""Modular track section with rails, sleepers, and fasteners."""

from __future__ import annotations

import math
from typing import List

import bpy

from app.config.geometry import TrackGeometryConfig
from app.geometry.layout import TrackSectionLayout
from app.geometry.utils import move_to_collection, parent_object, replace_material


class TrackSection:
    """
    Represents a single modular section of railway track.

    Creates an H-shaped assembly (top view: -- : | : --):
      - Two parallel rails
      - Three-piece sleeper (left outer, middle, right outer)
      - Eight fastener cylinders distributed across the sleeper pieces

    All geometry dimensions come from a TrackGeometryConfig.
    section_pitch (the Y span of this section) is derived:
        section_pitch = config.sleeper_length / config.sleeper_pitch_ratio
    """

    SECTION_PARENT_ROLE = "section_parent"
    LEFT_RAIL_ROLE = "left_rail"
    RIGHT_RAIL_ROLE = "right_rail"
    SLEEPER_ROLE = "sleeper"
    FASTENER_ROLE = "fastener"

    def __init__(
        self,
        config: TrackGeometryConfig | None = None,
        rail_material=None,
        sleeper_material=None,
        fastener_material=None,
    ):
        self.config = config if config is not None else TrackGeometryConfig()
        self.rail_material = rail_material
        self.sleeper_material = sleeper_material
        self.fastener_material = fastener_material

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
        cfg = self.config
        bpy.ops.mesh.primitive_cube_add(size=1)
        rail = bpy.context.active_object
        rail.name = "RailPiece"
        rail.scale = (cfg.rail_width, cfg.section_pitch, cfg.rail_height)
        rail.location = (x + x_offset, y, self._rail_center_z(z))
        rail.rotation_euler[2] = math.radians(cfg.rail_angle)
        self._register(rail, role=role, collection=collection,
                       parent=self.section_parent, material=self.rail_material)
        return rail

    def _create_sleeper_piece(self, *, x_pos, width, parent_location, collection, name) -> object:
        _, y, z = parent_location
        cfg = self.config
        bpy.ops.mesh.primitive_cube_add(size=1)
        sleeper = bpy.context.active_object
        sleeper.name = name
        sleeper.scale = (width, cfg.sleeper_length, cfg.sleeper_height)
        sleeper.location = (x_pos, y, self._sleeper_center_z(z))
        self._register(sleeper, role=self.SLEEPER_ROLE, collection=collection,
                       parent=self.section_parent, material=self.sleeper_material)
        return sleeper

    def _create_fasteners(self, parent_location, *, collection) -> List[object]:
        x, y, z = parent_location
        cfg = self.config
        layout = self._compute_layout(x)

        x_inset = max(cfg.screw_radius * 1.4, 0.01)
        outer_ratio = 0.65
        sw, mw = layout.side_sleeper_width, layout.middle_sleeper_width
        pair_x_positions = [
            layout.left_sleeper_x  - sw / 2 + sw * outer_ratio,
            layout.middle_sleeper_x - mw / 2 + x_inset,
            layout.middle_sleeper_x + mw / 2 - x_inset,
            layout.right_sleeper_x  + sw / 2 - sw * outer_ratio,
        ]
        pair_offset_y = max(cfg.sleeper_length * 0.24, 0.02)
        screw_z = self._sleeper_top_z(z) + cfg.screw_length / 2

        return [
            self._create_screw(px, sy, screw_z, collection=collection)
            for px in pair_x_positions
            for sy in (y - pair_offset_y, y + pair_offset_y)
        ]

    def _create_screw(self, x, y, z, *, collection) -> object:
        cfg = self.config
        bpy.ops.mesh.primitive_cylinder_add(
            radius=cfg.screw_radius, depth=cfg.screw_length, location=(x, y, z)
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
        cfg = self.config
        left_rail_x  = center_x - cfg.rail_spacing / 2
        right_rail_x = center_x + cfg.rail_spacing / 2

        side_sleeper_width = max(cfg.rail_width * 1.2, 0.08) * 2

        middle_edge_left  = left_rail_x  + cfg.rail_width / 2
        middle_edge_right = right_rail_x - cfg.rail_width / 2
        middle_sleeper_width = max(middle_edge_right - middle_edge_left, cfg.rail_width)
        middle_sleeper_x = (middle_edge_left + middle_edge_right) / 2

        left_sleeper_x  = left_rail_x  - cfg.rail_width / 2 - side_sleeper_width / 2
        right_sleeper_x = right_rail_x + cfg.rail_width / 2 + side_sleeper_width / 2

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
    # Geometry serialisation (used by cache key computation)
    # ------------------------------------------------------------------

    def geometry_payload(self) -> dict:
        """Return all geometry parameters as a plain dict for cache hashing."""
        return self.config.to_dict()

    # ------------------------------------------------------------------
    # Z-axis helpers
    # ------------------------------------------------------------------

    def _sleeper_center_z(self, base_z: float) -> float:
        return base_z + self.config.sleeper_height / 2

    def _sleeper_top_z(self, base_z: float) -> float:
        return self._sleeper_center_z(base_z) + self.config.sleeper_height / 2

    def _rail_center_z(self, base_z: float) -> float:
        return self._sleeper_top_z(base_z) + self.config.rail_height / 2 + self.config.rail_lift - self._rail_drop()

    def _rail_drop(self) -> float:
        """Lower rails slightly so fasteners remain visible in render."""
        cfg = self.config
        return min(
            max(cfg.screw_radius, 0.4 * cfg.screw_length),
            0.25 * cfg.rail_height,
            0.25 * cfg.sleeper_height,
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
