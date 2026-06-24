import bpy

from app.config import PipelineSettings
from app.config.geometry import TrackGeometryConfig
from app.geometry.cache import TrackSectionCache, DefectiveSectionCache
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

    def _load_geometry_config(self) -> TrackGeometryConfig:
        path = getattr(self.settings, "geometry_config_path", None)
        if path:
            return TrackGeometryConfig.from_yaml(path)
        return TrackGeometryConfig()

    def build(self) -> None:
        print("Modeling geometry (modular approach)...")

        geometry_cfg = self._load_geometry_config()
        # section_pitch is derived: sleeper_length / sleeper_pitch_ratio
        section_pitch = geometry_cfg.section_pitch

        rail_mat     = self.materials.create_rail_material()
        sleeper_mat  = self.materials.create_sleeper_material()
        fastener_mat = self.materials.create_fastener_material()
        grass_mat    = self.materials.create_grass_material()

        track_length = self.settings.track_length
        section_z = 0.1

        bpy.ops.mesh.primitive_plane_add(size=1, location=(0, track_length / 2, -0.3))
        grass = bpy.context.active_object
        grass.name = "GrassGround"
        grass.scale = (100, track_length, 1)
        grass.data.materials.append(grass_mat)

        num_sections = int(track_length / section_pitch) + 1

        prototype_section = TrackSection(
            config=geometry_cfg,
            rail_material=rail_mat,
            sleeper_material=sleeper_mat,
            fastener_material=fastener_mat,
        )
        prototype_collection = self.section_cache.get_or_create_prototype_collection(
            prototype_section
        )
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

        defect_selector = DefectSelector.default()
        defective_collections = {}
        for variant in defect_selector.all_variants():
            defective_col = self.defective_cache.get_or_create_defective_collection(
                TrackSection(config=geometry_cfg),
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
            y_pos = i * section_pitch
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
