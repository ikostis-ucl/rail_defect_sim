import bpy

from app.config import EnvironmentConfig, PipelineSettings, TrackGeometryConfig
from app.geometry.cache import DefectiveSectionCache, TrackSectionCache
from app.geometry.defects import DefectSelector
from app.geometry.track_section import TrackSection
from app.geometry.utils import move_to_collection
from app.materials import MaterialFactory
from app.progress import progress_iter


class TrackBuilder:
    """Creates rails, sleepers, fasteners, and terrain."""

    def __init__(self, settings: PipelineSettings, materials: MaterialFactory) -> None:
        self.settings = settings
        self.materials = materials
        self.section_cache = TrackSectionCache()
        self.defective_cache = DefectiveSectionCache()

    def build(self, geometry: TrackGeometryConfig) -> None:
        """Build the full track from *geometry*.

        The geometry config is passed in rather than loaded here so that the
        pipeline resolves it once and every consumer — track, camera datum,
        validation — sees the same values.
        """
        print("Modeling geometry (modular approach)...")

        rail_mat = self.materials.create_rail_material()
        sleeper_mat = self.materials.create_sleeper_material()
        fastener_mat = self.materials.create_fastener_material()
        grass_mat = self.materials.create_grass_material()

        track_length = self.settings.track_length
        section_spacing = geometry.section_pitch
        section_z = geometry.base_elevation

        self._build_ground(
            self.settings.environment.ground, track_length, section_z, grass_mat
        )

        num_sections = int(track_length / section_spacing) + 1

        prototype = TrackSection(config=geometry)
        prototype_collection = self.section_cache.get_or_create_prototype_collection(prototype)
        TrackSection.apply_materials_to_collection(
            prototype_collection,
            rail_material=rail_mat,
            sleeper_material=sleeper_mat,
            fastener_material=fastener_mat,
        )

        track_sections_collection = bpy.data.collections.new("ModularTrackSections")
        bpy.context.scene.collection.children.link(track_sections_collection)

        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        track_parent = bpy.context.active_object
        track_parent.name = "ModularTrack"
        move_to_collection(track_parent, track_sections_collection)

        force_defect = self.settings.force_defect
        seed = self.settings.seed
        print(f"Defect placement seed: {seed}")
        defect_selector = (
            DefectSelector.forced(force_defect, seed=seed)
            if force_defect
            else DefectSelector.default(seed=seed)
        )
        defective_collections = {}
        for variant in defect_selector.all_variants():
            defective_col = self.defective_cache.get_or_create_defective_collection(
                TrackSection(config=geometry),
                variant,
            )
            TrackSection.apply_materials_to_collection(
                defective_col,
                rail_material=rail_mat,
                sleeper_material=sleeper_mat,
                fastener_material=fastener_mat,
            )
            defective_collections[variant.identifier] = defective_col

        defect_count = 0
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
            is_defective = selected_variant is not None

            instance_col = (
                defective_collections[selected_variant.identifier]
                if is_defective
                else prototype_collection
            )
            prefix = "DefectiveSection" if is_defective else "TrackSectionInstance"
            obj = bpy.data.objects.new(f"{prefix}_{i:06d}", None)
            obj.empty_display_size = 0.05
            obj.instance_type = "COLLECTION"
            obj.instance_collection = instance_col
            obj.location = (0, y_pos, section_z)
            obj.parent = track_parent
            track_sections_collection.objects.link(obj)

            if is_defective:
                defect_count += 1

        print(
            f"Modular track created successfully. "
            f"{defect_count} defective section(s) out of {num_sections} total "
            f"({100 * defect_count / max(num_sections, 1):.1f} %)."
        )

    def _build_ground(self, ground_cfg, track_length, section_z, grass_mat) -> None:
        bpy.ops.mesh.primitive_plane_add(
            size=1, location=(0, track_length / 2, section_z + ground_cfg.z_offset)
        )
        grass = bpy.context.active_object
        grass.name = "GrassGround"
        grass.scale = (ground_cfg.half_width, track_length, 1)
        grass.data.materials.append(grass_mat)
