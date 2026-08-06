"""Scene builder — world, units, and lighting.

The *builder* half of the environment. The *data* half is
``app.config.environment.EnvironmentConfig``.
"""

import bpy

from app.config import EnvironmentConfig


class SceneSetup:
    """Handles high-level scene lifecycle setup."""

    def __init__(self, config: EnvironmentConfig | None = None) -> None:
        self.config = config if config is not None else EnvironmentConfig()

    def setup_metric_units(self) -> None:
        """Set scene unit system to metric with 1 Blender unit = 1 metre."""
        unit = bpy.context.scene.unit_settings
        unit.system = "METRIC"
        unit.scale_length = 1.0
        unit.length_unit = "METERS"

    def cleanup_scene(self) -> None:
        print("Cleaning up scene...")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

    def setup_world(self) -> None:
        world = bpy.context.scene.world
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs["Color"].default_value = self.config.world.background_color

    def create_lighting(self) -> None:
        print("Setting up lighting...")
        sun_cfg = self.config.sun
        bpy.ops.object.light_add(type="SUN", location=sun_cfg.location)
        sun = bpy.context.active_object
        sun.data.energy = sun_cfg.energy
        if hasattr(sun.data, "use_shadow"):
            sun.data.use_shadow = sun_cfg.cast_shadows
