"""Modular track section with rails, sleepers, and fasteners."""

from __future__ import annotations

import math
from typing import List

import bpy

from app.config.geometry import RailConfig, TrackGeometryConfig
from app.geometry.layout import TrackSectionLayout
from app.geometry.utils import move_to_collection, parent_object, replace_material


class TrackSection:
    """
    Represents a single modular section of railway track.

    Creates an H-shaped assembly (top view: -- : | : --):
      - Two parallel rails (left and right, each with its own RailConfig)
      - Three-piece sleeper (left outer, middle, right outer)
      - Eight fastener cylinders distributed across the sleeper pieces

    All geometry dimensions come from a TrackGeometryConfig.
    section_pitch (the Y span of this section) is derived:
        section_pitch = config.sleeper_depth / config.sleeper_pitch_ratio
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
        cfg = self.config
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
            width=layout.left_side_sleeper_width,
            parent_location=(x, y, z),
            collection=target_collection,
            name="SleeperLeft",
        )
        self.left_rail = self._create_rail(
            x_offset=layout.left_rail_x - x,
            parent_location=(x, y, z),
            rail_cfg=cfg.left_rail,
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
            rail_cfg=cfg.right_rail,
            role=self.RIGHT_RAIL_ROLE,
            collection=target_collection,
        )
        self.right_sleeper = self._create_sleeper_piece(
            x_pos=layout.right_sleeper_x,
            width=layout.right_side_sleeper_width,
            parent_location=(x, y, z),
            collection=target_collection,
            name="SleeperRight",
        )
        self.sleeper = self.middle_sleeper
        self.fasteners = self._create_fasteners(parent_location=(x, y, z), collection=target_collection)
        self.correct_contiguity(z)
        return self.section_parent

    # ------------------------------------------------------------------
    # Component builders
    # ------------------------------------------------------------------

    def _create_rail(self, x_offset, parent_location, *, rail_cfg: RailConfig, role, collection) -> object:
        x, y, z = parent_location
        cfg = self.config
        bpy.ops.mesh.primitive_cube_add(size=1)
        rail = bpy.context.active_object
        rail.name = "RailPiece"
        rail.scale = (rail_cfg.head_width, cfg.section_pitch, rail_cfg.height)
        rail.location = (x + x_offset, y, self._rail_center_z(z, rail_cfg))
        rail.rotation_euler[2] = math.radians(rail_cfg.angle)
        self._register(rail, role=role, collection=collection,
                       parent=self.section_parent, material=self.rail_material)
        return rail

    def _create_sleeper_piece(self, *, x_pos, width, parent_location, collection, name) -> object:
        _, y, z = parent_location
        cfg = self.config
        bpy.ops.mesh.primitive_cube_add(size=1)
        sleeper = bpy.context.active_object
        sleeper.name = name
        sleeper.scale = (width, cfg.sleeper_depth, cfg.sleeper_height)
        sleeper.location = (x_pos, y, self._sleeper_center_z(z))
        self._register(sleeper, role=self.SLEEPER_ROLE, collection=collection,
                       parent=self.section_parent, material=self.sleeper_material)
        return sleeper

    def _create_fasteners(self, parent_location, *, collection) -> List[object]:
        x, y, z = parent_location
        cfg = self.config
        layout = self._compute_layout(x)

        lr = cfg.left_rail
        rr = cfg.right_rail
        # Each clip is placed at the rail foot edge; cfg.screw_radius keeps it
        # just inside the foot so it visually grips the flange.
        clip = cfg.screw_radius
        pair_x_positions = [
            layout.left_rail_x  - lr.foot_width / 2 + clip,   # outer left clip
            layout.left_rail_x  + lr.foot_width / 2 - clip,   # inner left clip
            layout.right_rail_x - rr.foot_width / 2 + clip,   # inner right clip
            layout.right_rail_x + rr.foot_width / 2 - clip,   # outer right clip
        ]
        # Pairs 0 and 1 are on the left rail; pairs 2 and 3 are on the right rail.
        pair_rail_cfgs = [lr, lr, rr, rr]

        pair_offset_y = max(cfg.sleeper_depth * 0.24, 0.02)
        sleeper_top = self._sleeper_top_z(z)

        fasteners = []
        for px, rail_cfg in zip(pair_x_positions, pair_rail_cfgs):
            depth = self._fastener_depth(rail_cfg)
            screw_z = sleeper_top + depth / 2
            for sy in (y - pair_offset_y, y + pair_offset_y):
                fasteners.append(
                    self._create_screw(px, sy, screw_z, depth=depth, collection=collection)
                )
        return fasteners

    def _create_screw(self, x, y, z, *, depth: float, collection) -> object:
        cfg = self.config
        bpy.ops.mesh.primitive_cylinder_add(
            radius=cfg.screw_radius, depth=depth, location=(x, y, z)
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
        lr = cfg.left_rail
        rr = cfg.right_rail

        left_rail_x  = center_x - cfg.rail_spacing / 2
        right_rail_x = center_x + cfg.rail_spacing / 2

        # Outer sleepers match the rail foot width — the foot is the structural
        # reference for fastener seats and sleeper extent.
        left_side_sleeper_width  = lr.foot_width
        right_side_sleeper_width = rr.foot_width

        # Middle sleeper spans the gap between the inner edges of both rail feet.
        middle_edge_left  = left_rail_x  + lr.foot_width / 2
        middle_edge_right = right_rail_x - rr.foot_width / 2
        middle_sleeper_width = max(middle_edge_right - middle_edge_left,
                                   max(lr.foot_width, rr.foot_width))
        middle_sleeper_x = (middle_edge_left + middle_edge_right) / 2

        # Outer sleepers sit immediately beyond the outer rail foot edge.
        left_sleeper_x  = left_rail_x  - lr.foot_width / 2 - left_side_sleeper_width / 2
        right_sleeper_x = right_rail_x + rr.foot_width / 2 + right_side_sleeper_width / 2

        return TrackSectionLayout(
            left_sleeper_x=left_sleeper_x,
            left_rail_x=left_rail_x,
            middle_sleeper_x=middle_sleeper_x,
            middle_sleeper_width=middle_sleeper_width,
            right_rail_x=right_rail_x,
            right_sleeper_x=right_sleeper_x,
            left_side_sleeper_width=left_side_sleeper_width,
            right_side_sleeper_width=right_side_sleeper_width,
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

    def _rail_center_z(self, base_z: float, rail_cfg: RailConfig) -> float:
        """Rail foot rests on the elastomeric pad which sits on the sleeper surface.

        Contact chain (bottom → top):
          sleeper top = base_z + sleeper_height
          pad top     = sleeper_top + pad_thickness   ← rail foot starts here
          rail centre = pad_top + height/2 + lift
        """
        return (
            self._sleeper_top_z(base_z)
            + rail_cfg.pad_thickness
            + rail_cfg.height / 2
            + rail_cfg.lift
        )

    def _fastener_depth(self, rail_cfg: RailConfig) -> float:
        """Fastener length that guarantees the clip reaches the rail foot.

        Standard length is used when the rail sits flush on its pad.  When a
        defect introduces a *lift* gap, the fastener grows to bridge it so the
        clip stays in contact with the rail flange rather than floating in air.

        The standard dimension is the lower bound; the rendered dimension is
        always at least pad_thickness + lift so there is no gap.
        """
        gap = rail_cfg.pad_thickness + rail_cfg.lift
        return max(self.config.screw_length, gap)

    # ------------------------------------------------------------------
    # Contiguity correction
    # ------------------------------------------------------------------

    def correct_contiguity(self, base_z: float = 0.0) -> None:
        """Re-apply exact Z positions to guarantee all components are contiguous.

        Call this after build() (already done automatically) and again after
        any defect.apply() that modifies rail lift or sleeper height.

        Contact chain enforced (Z axis, bottom → top):
          sleeper bottom  = base_z
          sleeper top     = base_z + sleeper_height
          pad top         = sleeper_top + pad_thickness   ← rail foot rests here
          rail centre     = pad_top + height/2 + lift
          fastener base   = sleeper_top                   ← clip on sleeper surface
          fastener top    = sleeper_top + fastener_depth  ← grows to bridge lift gap

        When lift > 0 the fastener scale.z is adjusted so the clip still grips
        the rail flange instead of leaving empty space.  The standard dimension
        from the profile is the *initial* value only; correctness takes priority.
        """
        sleeper_top = self._sleeper_top_z(base_z)

        for rail_obj, rail_cfg in (
            (self.left_rail,  self.config.left_rail),
            (self.right_rail, self.config.right_rail),
        ):
            if rail_obj is not None:
                rail_obj.location.z = (
                    sleeper_top
                    + rail_cfg.pad_thickness
                    + rail_cfg.height / 2
                    + rail_cfg.lift
                )

        # Index map (8 fasteners, 4 pairs of 2):
        #   [0,1] outer-left   → left rail
        #   [2,3] inner-left   → left rail
        #   [4,5] inner-right  → right rail
        #   [6,7] outer-right  → right rail
        rail_by_fastener = (
            [self.config.left_rail]  * 4
            + [self.config.right_rail] * 4
        )
        nominal = self.config.screw_length
        for fastener, rail_cfg in zip(self.fasteners, rail_by_fastener):
            depth = self._fastener_depth(rail_cfg)
            fastener.location.z = sleeper_top + depth / 2
            if depth != nominal:
                fastener.scale.z = depth / nominal

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
