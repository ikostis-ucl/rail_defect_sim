import bpy


class SceneSetup:
    """Handles high-level scene lifecycle setup."""

    def cleanup_scene(self) -> None:
        print("Cleaning up scene...")
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()

    def setup_world(self) -> None:
        world = bpy.context.scene.world
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs["Color"].default_value = (0.01, 0.005, 0.002, 1.0)

    def create_lighting(self) -> None:
        print("Setting up lighting...")
        bpy.ops.object.light_add(type="SUN", location=(5, 5, 10))
        sun = bpy.context.active_object
        sun.data.energy = 5.0
        # Disable cast shadows for flatter diagnostic renders.
        if hasattr(sun.data, "use_shadow"):
            sun.data.use_shadow = False

