import bpy

from app.config import PipelineSettings
from app.geometry.track_section_cache import TrackSectionCache
from app.geometry.track_defects import DefectSelector, DefectiveSectionCache
from app.materials import MaterialFactory
from app.progress import progress_iter
from app.geometry.track_section import TrackSection


class TrackBuilder:
    """Creates rails, sleepers, clips, ballast, and terrain."""

    def __init__(self, settings: PipelineSettings, materials: MaterialFactory) -> None:
        self.settings = settings
        self.materials = materials
        self.section_cache = TrackSectionCache()
        self.defective_cache = DefectiveSectionCache()

    def build(self) -> None:
        # Single geometry path for both draft and final to keep outputs consistent.
        self.build_modular_track()


    def build_modular_track(self) -> None:
        """
        Alternative build method using modular TrackSection components.
        
        This approach creates individual track sections that can later have
        defects applied (e.g., skewed ballast, missing fasteners, etc.).
        """
        print("Modeling geometry (modular approach)...")

        rail_mat = self.materials.create_rail_material()
        ballast_mat = self.materials.create_ballast_material()
        fastener_mat = self.materials.create_fastener_material()
        grass_mat = self.materials.create_grass_material()

        track_length = self.settings.track_length
        ballast_length = 0.15 * 0.72
        # Increase spacing between consecutive ballast sections along the track.
        section_spacing = 0.18
        # Rails should still connect from one section to the next.
        rail_length = section_spacing
        ballast_length_ratio = ballast_length / section_spacing
        section_z = 0.1

        # Create ground
        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, track_length / 2, -0.3))
        grass = bpy.context.active_object
        grass.name = "GrassGround"
        grass.scale = (100, track_length, 1)
        grass.data.materials.append(grass_mat)

        # Calculate number of sections needed
        num_sections = int(track_length / section_spacing) + 1

        prototype_section = TrackSection(
            length=section_spacing,
            rail_spacing=1.4,
            rail_height=0.16,
            rail_width=0.06,
            ballast_height=0.12,
            rail_length=rail_length,
            ballast_length_ratio=ballast_length_ratio,
        )
        prototype_collection = self.section_cache.get_or_create_prototype_collection(prototype_section)
        TrackSection.apply_materials_to_collection(
            prototype_collection,
            rail_material=rail_mat,
            ballast_material=ballast_mat,
            fastener_material=fastener_mat,
        )

        track_sections_collection = bpy.data.collections.new("ModularTrackSections")
        bpy.context.scene.collection.children.link(track_sections_collection)

        # Create parent collection for all track sections
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        track_parent = bpy.context.active_object
        track_parent.name = "ModularTrack"
        self._move_object_to_collection(track_parent, track_sections_collection)

        # Pre-build and cache all defective section variants.
        defect_selector = DefectSelector.default()
        defective_collections = {}
        prototype_section_for_defects = TrackSection(
            length=section_spacing,
            rail_spacing=1.4,
            rail_height=0.16,
            rail_width=0.06,
            ballast_height=0.12,
            rail_length=rail_length,
            ballast_length_ratio=ballast_length_ratio,
        )
        for variant in defect_selector.all_variants():
            defective_col = self.defective_cache.get_or_create_defective_collection(
                prototype_section_for_defects,
                defect_name=variant.defect_name,
                defect_params=variant.defect_params,
            )
            TrackSection.apply_materials_to_collection(
                defective_col,
                rail_material=rail_mat,
                ballast_material=ballast_mat,
                fastener_material=fastener_mat,
            )
            defective_collections[variant.identifier] = defective_col

        defect_count = 0

        # Build individual sections
        print(f"Creating {num_sections} modular track sections...")
        for i in progress_iter(
            range(num_sections),
            desc="Creating modular track sections",
            total=num_sections,
            unit="section",
        ):
            y_pos = i * section_spacing
            if y_pos > track_length:
                break

            selected_variant = defect_selector.select_variant()

            if selected_variant is None:
                # ── Normal section: efficient collection instance ────────
                section_instance = bpy.data.objects.new(f"TrackSectionInstance_{i:06d}", None)
                section_instance.empty_display_size = 0.05
                section_instance.instance_type = "COLLECTION"
                section_instance.instance_collection = prototype_collection
                section_instance.location = (0, y_pos, section_z)
                section_instance.parent = track_parent
                track_sections_collection.objects.link(section_instance)
            else:
                # ── Defective section: cached collection instance ────────
                defective_col = defective_collections[selected_variant.identifier]
                section_instance = bpy.data.objects.new(f"DefectiveSection_{i:06d}", None)
                section_instance.empty_display_size = 0.05
                section_instance.instance_type = "COLLECTION"
                section_instance.instance_collection = defective_col
                section_instance.location = (0, y_pos, section_z)
                section_instance.parent = track_parent
                track_sections_collection.objects.link(section_instance)
                defect_count += 1

        print(
            f"Modular track created successfully. "
            f"{defect_count} defective section(s) out of {num_sections} total "
            f"({100 * defect_count / max(num_sections, 1):.1f} %)."
        )

    @staticmethod
    def _move_object_to_collection(obj, target_collection) -> None:
        for existing_collection in list(obj.users_collection):
            existing_collection.objects.unlink(obj)
        target_collection.objects.link(obj)

