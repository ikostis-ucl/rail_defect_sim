import bpy

from app.config import PipelineSettings


class CameraAnimator:
    """Creates camera rig and applies movement + vibration animation."""

    def __init__(self, settings: PipelineSettings) -> None:
        self.settings = settings

    @staticmethod
    def setup_camera():
        print("Setting up camera...")
        # Lower camera altitude so rails/ballast fill most of the frame.
        bpy.ops.object.camera_add(location=(0, 0, 2.45), rotation=(0, 0, 0))
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.data.type = "PERSP"
        cam.data.lens = 35
        return cam

    def animate(self, camera) -> None:
        print("Animating camera with train physics...")

        if not camera.animation_data:
            camera.animation_data_create()
        camera.animation_data_clear()

        fps = self.settings.fps
        start_frame = self.settings.start_frame
        total_frames = self.settings.total_frames
        accel_duration = 10 * fps

        camera.location.y = 0
        camera.keyframe_insert(data_path="location", frame=start_frame, index=1)

        total_distance = self.settings.base_speed_units_per_frame * total_frames
        camera.location.y = total_distance
        camera.keyframe_insert(data_path="location", frame=total_frames, index=1)

        action = camera.animation_data.action

        if hasattr(action, "fcurves"):
            fcurve_y = action.fcurves.find("location", index=1)
        else:
            fcurve_y = action.fcurve_ensure_for_datablock(camera, data_path="location", index=1)

        if fcurve_y:
            fcurve_y.extrapolation = "LINEAR"
            key_start = fcurve_y.keyframe_points[0]
            key_start.interpolation = "BEZIER"
            key_start.handle_right = (start_frame + accel_duration, 0)

            noise_mod = fcurve_y.modifiers.new(type="NOISE")
            noise_mod.scale = 100.0
            noise_mod.strength = 5.0

        if hasattr(action, "fcurves"):
            fcurve_z = action.fcurves.new(data_path="location", index=2)
            fcurve_rot_x = action.fcurves.new(data_path="rotation_euler", index=0)
        else:
            fcurve_z = action.fcurve_ensure_for_datablock(camera, data_path="location", index=2)
            fcurve_rot_x = action.fcurve_ensure_for_datablock(camera, data_path="rotation_euler", index=0)

        mod_z = fcurve_z.modifiers.new(type="NOISE")
        mod_z.scale = 2.0
        mod_z.strength = 0.05

        mod_rot = fcurve_rot_x.modifiers.new(type="NOISE")
        mod_rot.scale = 5.0
        mod_rot.strength = 0.002

