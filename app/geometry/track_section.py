"""Modular track section with rails, ballast, and fasteners (screws)."""

import bpy
from typing import List


class TrackSection:
    SECTION_PARENT_ROLE = "section_parent"
    LEFT_RAIL_ROLE = "left_rail"
    RIGHT_RAIL_ROLE = "right_rail"
    BALLAST_ROLE = "ballast"
    FASTENER_ROLE = "fastener"

    """
    Represents a single modular section of railway track.
    
    Creates an H-shaped assembly consisting of:
    - Two parallel rail pieces (vertical elements of the H)
    - One ballast/sleeper (horizontal element of the H)
    - Fasteners (screws) positioned realistically:
      * Two screws stacked vertically on each side of the ballast
      * One screw between each pair and the rail
      
    Pattern visualization (top view):
        -- : . | . : --
    Where: -- = ballast, | = rail, : = screw pair, . = single screw
    
    This modular design allows for:
    - Easy defect simulation (skewing, missing fasteners, etc.)
    - Realistic rail geometry
    - Future animations of individual components
    """

    def __init__(
        self,
        rail_material=None,
        ballast_material=None,
        fastener_material=None,
        length: float = 0.15,
        rail_spacing: float = 1.4,
        rail_height: float = 0.16,
        rail_width: float = 0.06,
        ballast_height: float = 0.12,
        rail_lift: float = 0.0,
        rail_length: float | None = None,
        ballast_length_ratio: float = 0.72,
    ):
        """
        Initialize a track section.
        
        Args:
            rail_material: Material for the rail pieces
            ballast_material: Material for the ballast/sleeper
            fastener_material: Material for the screws
            length: Length of the section along the track (Y-axis)
            rail_spacing: Distance between the two rails (X-axis)
            rail_height: Height of each rail (Z-axis)
            rail_width: Width of each rail (X-axis)
            ballast_height: Height of the ballast (Z-axis)
        """
        self.rail_material = rail_material
        self.ballast_material = ballast_material
        self.fastener_material = fastener_material
        
        self.length = length
        self.rail_spacing = rail_spacing
        self.rail_height = rail_height
        self.rail_width = rail_width
        self.ballast_height = ballast_height
        self.rail_lift = rail_lift
        self.rail_length = rail_length if rail_length is not None else length
        
        # Screw dimensions
        self.screw_radius = 0.015
        self.screw_length = 0.05
        self.ballast_length_ratio = ballast_length_ratio
        
        # Store component objects for potential defect application
        self.left_rail = None
        self.right_rail = None
        self.left_ballast = None
        self.middle_ballast = None
        self.right_ballast = None
        self.ballast = None
        self.fasteners: List[object] = []
        self.section_parent = None

    def build(self, location=(0, 0, 0), *, target_collection=None, parent=None) -> object:
        """
        Build the complete track section at the given location.
        
        Args:
            location: (x, y, z) position for the section origin
            
        Returns:
            The parent object containing all section components
        """
        x, y, z = location
        target_collection = target_collection or bpy.context.scene.collection
        
        # Create parent empty to group all components
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=location)
        self.section_parent = bpy.context.active_object
        self.section_parent.name = "TrackSection"
        self._register_object(
            self.section_parent,
            role=self.SECTION_PARENT_ROLE,
            target_collection=target_collection,
        )
        if parent is not None:
            self._parent_object(self.section_parent, parent)
        
        layout = self._compute_layout_x_positions(x)

        # Build core in explicit cross-order: -- | ----- | --
        self.left_ballast = self._create_ballast_piece(
            x_pos=layout["left_ballast_x"],
            width=layout["side_ballast_width"],
            parent_location=(x, y, z),
            target_collection=target_collection,
            name="BallastLeft",
        )

        self.left_rail = self._create_rail(
            x_offset=layout["left_rail_x"] - x,
            parent_location=(x, y, z),
            role=self.LEFT_RAIL_ROLE,
            target_collection=target_collection,
        )

        self.middle_ballast = self._create_ballast_piece(
            x_pos=layout["middle_ballast_x"],
            width=layout["middle_ballast_width"],
            parent_location=(x, y, z),
            target_collection=target_collection,
            name="BallastMiddle",
        )

        self.right_rail = self._create_rail(
            x_offset=layout["right_rail_x"] - x,
            parent_location=(x, y, z),
            role=self.RIGHT_RAIL_ROLE,
            target_collection=target_collection,
        )

        self.right_ballast = self._create_ballast_piece(
            x_pos=layout["right_ballast_x"],
            width=layout["side_ballast_width"],
            parent_location=(x, y, z),
            target_collection=target_collection,
            name="BallastRight",
        )

        # Keep backward-compatible accessor behavior by treating middle as main ballast.
        self.ballast = self.middle_ballast
        
        # Add fasteners
        self.fasteners = self._create_fasteners(
            parent_location=(x, y, z),
            target_collection=target_collection,
        )
        
        return self.section_parent

    def _create_rail(
        self,
        x_offset: float,
        parent_location: tuple,
        *,
        role: str,
        target_collection,
    ) -> object:
        """Create a single rail piece."""
        x, y, z = parent_location
        
        bpy.ops.mesh.primitive_cube_add(size=1)
        rail = bpy.context.active_object
        rail.name = "RailPiece"
        
        # Scale: width (X), length (Y), height (Z)
        rail.scale = (self.rail_width, self.rail_length, self.rail_height)
        
        # Position relative to section center
        rail.location = (x + x_offset, y, self._rail_center_z(z))

        self._register_object(
            rail,
            role=role,
            target_collection=target_collection,
            parent=self.section_parent,
            material=self.rail_material,
        )
        
        return rail

    def _create_ballast_piece(
        self,
        *,
        x_pos: float,
        width: float,
        parent_location: tuple,
        target_collection,
        name: str,
    ) -> object:
        """Create one ballast piece used in the -- | ----- | -- cross layout."""
        _, y, z = parent_location
        
        bpy.ops.mesh.primitive_cube_add(size=1)
        ballast = bpy.context.active_object
        ballast.name = name
        
        # Scale: width (X), length (Y), height (Z)
        ballast.scale = (width, self.length * self.ballast_length_ratio, self.ballast_height)
        
        # Keep all ballast pieces on the same Z level.
        ballast_z = self._ballast_center_z(z)
        ballast.location = (x_pos, y, ballast_z)

        self._register_object(
            ballast,
            role=self.BALLAST_ROLE,
            target_collection=target_collection,
            parent=self.section_parent,
            material=self.ballast_material,
        )
        
        return ballast

    def _compute_layout_x_positions(self, center_x: float) -> dict[str, float]:
        """Compute cross-section positions for -- | ----- | --."""
        left_rail_x = center_x - self.rail_spacing / 2
        right_rail_x = center_x + self.rail_spacing / 2

        # Ballast pieces within a cross-section still meet the rail directly.
        edge_gap = 0.0
        base_side_ballast_width = max(self.rail_width * 1.2, 0.08)
        side_ballast_width = base_side_ballast_width * 2

        middle_edge_left = left_rail_x + self.rail_width / 2 + edge_gap
        middle_edge_right = right_rail_x - self.rail_width / 2 - edge_gap
        middle_ballast_width = max(middle_edge_right - middle_edge_left, self.rail_width)
        middle_ballast_x = (middle_edge_left + middle_edge_right) / 2

        # Side ballast pieces touch rail outer faces without overlap.
        left_ballast_x = left_rail_x - self.rail_width / 2 - side_ballast_width / 2
        right_ballast_x = right_rail_x + self.rail_width / 2 + side_ballast_width / 2

        return {
            "left_ballast_x": left_ballast_x,
            "left_rail_x": left_rail_x,
            "middle_ballast_x": middle_ballast_x,
            "middle_ballast_width": middle_ballast_width,
            "right_rail_x": right_rail_x,
            "right_ballast_x": right_ballast_x,
            "side_ballast_width": side_ballast_width,
            "edge_gap": edge_gap,
        }

    def _create_fasteners(self, parent_location: tuple, *, target_collection) -> List[object]:
        """
        Create fasteners (screws) in a realistic pattern.
        
        Pattern (per side):
        - Two screws stacked vertically on the ballast (near rail)
        - One screw between the pair and the rail center
        """
        fasteners = []
        x, y, z = parent_location
        
        layout = self._compute_layout_x_positions(x)

        # Place pairs on ballast pieces:
        # left ballast (right end), middle ballast (left+right ends), right ballast (left end).
        side_width = layout["side_ballast_width"]
        middle_width = layout["middle_ballast_width"]
        x_inset = max(self.screw_radius * 1.4, 0.01)
        outer_fastener_ratio = 0.65
        fastener_pair_x_positions = [
            layout["left_ballast_x"] - side_width / 2 + side_width * outer_fastener_ratio,
            layout["middle_ballast_x"] - middle_width / 2 + x_inset,
            layout["middle_ballast_x"] + middle_width / 2 - x_inset,
            layout["right_ballast_x"] + side_width / 2 - side_width * outer_fastener_ratio,
        ]

        # Two screws per pair (front/back along track) => 4 pairs total, 8 screws total.
        pair_offset_y = max((self.length * self.ballast_length_ratio) * 0.24, 0.02)
        screw_y_positions = [y - pair_offset_y, y + pair_offset_y]
        ballast_top_z = self._ballast_top_z(z)
        screw_center_z = ballast_top_z + self.screw_length / 2

        for pair_x in fastener_pair_x_positions:
            for screw_y in screw_y_positions:
                fasteners.append(
                    self._create_screw(
                        pair_x,
                        screw_y,
                        screw_center_z,
                        target_collection=target_collection,
                    )
                )
        
        return fasteners

    def _create_screw(self, x: float, y: float, z: float, *, target_collection) -> object:
        """Create a single screw (represented as a small sphere/cylinder)."""
        # Using a small cylinder to represent a screw head and shaft
        bpy.ops.mesh.primitive_cylinder_add(
            radius=self.screw_radius,
            depth=self.screw_length,
            location=(x, y, z)
        )
        screw = bpy.context.active_object
        screw.name = "Fastener"

        self._register_object(
            screw,
            role=self.FASTENER_ROLE,
            target_collection=target_collection,
            parent=self.section_parent,
            material=self.fastener_material,
        )
        
        return screw

    def geometry_payload(self) -> dict[str, float]:
        """Return the geometry-defining payload used for cache keys."""
        return {
            "length": self.length,
            "rail_spacing": self.rail_spacing,
            "rail_height": self.rail_height,
            "rail_width": self.rail_width,
            "ballast_height": self.ballast_height,
            "rail_lift": self.rail_lift,
            "rail_length": self.rail_length,
            "ballast_length_ratio": self.ballast_length_ratio,
            "screw_radius": self.screw_radius,
            "screw_length": self.screw_length,
        }

    def _ballast_center_z(self, base_z: float) -> float:
        return base_z + self.ballast_height / 2

    def _ballast_top_z(self, base_z: float) -> float:
        return self._ballast_center_z(base_z) + self.ballast_height / 2

    def _rail_center_z(self, base_z: float) -> float:
        return self._ballast_top_z(base_z) + self.rail_height / 2 + self.rail_lift - self._rail_drop()

    def _rail_drop(self) -> float:
        """Lower rails slightly so nearby fasteners remain visible in render."""
        return min(
            max(self.screw_radius, 0.4 * self.screw_length),
            0.25 * self.rail_height,
            0.25 * self.ballast_height,
        )

    @classmethod
    def apply_materials_to_collection(
        cls,
        collection,
        *,
        rail_material=None,
        ballast_material=None,
        fastener_material=None,
    ) -> None:
        """Apply current-run materials to a cached prototype collection."""
        for obj in collection.objects:
            role = obj.get("track_section_role")
            if role in {cls.LEFT_RAIL_ROLE, cls.RIGHT_RAIL_ROLE}:
                cls._replace_object_material(obj, rail_material)
            elif role == cls.BALLAST_ROLE:
                cls._replace_object_material(obj, ballast_material)
            elif role == cls.FASTENER_ROLE:
                cls._replace_object_material(obj, fastener_material)

    def _register_object(
        self,
        obj,
        *,
        role: str,
        target_collection,
        parent=None,
        material=None,
    ) -> None:
        obj["track_section_role"] = role
        self._move_object_to_collection(obj, target_collection)
        if parent is not None:
            self._parent_object(obj, parent)
        self._replace_object_material(obj, material)

    @staticmethod
    def _parent_object(obj, parent) -> None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()

    @staticmethod
    def _move_object_to_collection(obj, target_collection) -> None:
        if target_collection is None:
            return
        for existing_collection in list(obj.users_collection):
            existing_collection.objects.unlink(obj)
        target_collection.objects.link(obj)

    @staticmethod
    def _replace_object_material(obj, material) -> None:
        if material is None or getattr(obj, "data", None) is None:
            return
        materials = getattr(obj.data, "materials", None)
        if materials is None:
            return
        materials.clear()
        materials.append(material)

    def get_all_components(self) -> List[object]:
        """Return all component objects in this section."""
        components = []
        if self.left_rail:
            components.append(self.left_rail)
        if self.right_rail:
            components.append(self.right_rail)
        if self.ballast:
            components.append(self.ballast)
        if self.left_ballast and self.left_ballast is not self.ballast:
            components.append(self.left_ballast)
        if self.middle_ballast and self.middle_ballast is not self.ballast:
            components.append(self.middle_ballast)
        if self.right_ballast and self.right_ballast is not self.ballast:
            components.append(self.right_ballast)
        components.extend(self.fasteners)
        return components

    def get_ballast(self) -> object:
        """Return the ballast object (useful for applying skew defects)."""
        return self.ballast

    def get_rails(self) -> tuple:
        """Return both rail objects as a tuple."""
        return (self.left_rail, self.right_rail)

