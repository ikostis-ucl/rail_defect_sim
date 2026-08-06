"""Camera builder — turns a CameraConfig into an animated Blender camera.

This is the *builder* half of the camera. The *data* half is
``app.config.camera.CameraConfig``, which is ``bpy``-free and holds pose,
optics, and sensor.
"""

import math

import bpy
import mathutils

from app.config import PipelineSettings, TrackGeometryConfig


class CameraAnimator:
    """Creates the camera rig and applies movement + vibration animation."""

    def __init__(self, settings: PipelineSettings) -> None:
        self.settings = settings

    @property
    def config(self):
        return self.settings.camera

    def setup_camera(self, geometry: TrackGeometryConfig):
        """Create the scene camera.

        *geometry* supplies the railhead datum, so a camera configured with
        ``height_reference='rail_top'`` keeps its clearance above the rail when
        the track geometry changes. With ``'world'`` the geometry is unused and
        the configured height is taken as an absolute Z.
        """
        print("Setting up camera...")
        cfg = self.config
        render = self.settings.render

        world_z = cfg.resolve_world_height(geometry.rail_top_z)

        # Compose orientation as a standard yaw → tilt → roll camera rig:
        #   tilt about X (0 = looking straight down -Z, 90 = looking forward +Y),
        #   yaw about world Z (pan left/right), roll about the view axis (bank).
        rot = (
            mathutils.Matrix.Rotation(math.radians(cfg.yaw_deg), 4, "Z")
            @ mathutils.Matrix.Rotation(math.radians(cfg.tilt_deg), 4, "X")
            @ mathutils.Matrix.Rotation(math.radians(cfg.roll_deg), 4, "Z")
        )

        bpy.ops.object.camera_add(
            location=(cfg.lateral_offset, 0, world_z),
            rotation=rot.to_euler(),
        )
        cam = bpy.context.active_object
        bpy.context.scene.camera = cam
        cam.data.type = "PERSP"
        cam.data.lens = cfg.lens_mm
        # Set the sensor explicitly rather than relying on Blender's default, so
        # the field of view actually rendered matches what CameraConfig computes.
        cam.data.sensor_width = cfg.sensor_width_mm

        h_fov, v_fov = cfg.fov_deg(render.resolution_x, render.resolution_y)
        print(
            f"Camera at Z={world_z:.3f} m "
            f"({cfg.height:.3f} m relative to {cfg.height_reference}), "
            f"FOV {h_fov:.1f}° x {v_fov:.1f}°"
        )
        return cam

    def animate(self, camera) -> None:
        print("Animating camera with train physics...")

        if not camera.animation_data:
            camera.animation_data_create()
        camera.animation_data_clear()

        render = self.settings.render
        fps = render.fps
        start_frame = render.start_frame
        total_frames = render.total_frames
        accel_duration = self.config.accel_seconds * fps

        camera.location.y = 0
        camera.keyframe_insert(data_path="location", frame=start_frame, index=1)

        camera.location.y = self.settings.total_travel_distance
        camera.keyframe_insert(data_path="location", frame=total_frames, index=1)

        action = camera.animation_data.action

        if hasattr(action, "fcurves"):
            fcurve_y = action.fcurves.find("location", index=1)
        else:
            fcurve_y = action.fcurve_ensure_for_datablock(camera, data_path="location", index=1)

        if fcurve_y:
            fcurve_y.extrapolation = "LINEAR"
            key_start = fcurve_y.keyframe_points[0]
            if accel_duration > 0:
                # Ease-in: start slow, ramp up to cruising speed over accel_duration.
                key_start.interpolation = "BEZIER"
                key_start.handle_right = (start_frame + accel_duration, 0)
            else:
                # No acceleration: constant velocity across the whole clip.
                key_start.interpolation = "LINEAR"

            noise_mod = fcurve_y.modifiers.new(type="NOISE")
            noise_mod.scale = 100.0
            noise_mod.strength = 5.0

        # Capture the configured base height and tilt, then keyframe them as
        # constants. The vibration NOISE modifiers below add to the keyframed
        # value, so they jitter *around* the configured pose instead of
        # oscillating around zero (which would wipe out height and tilt).
        base_z = camera.location.z
        base_rot_x = camera.rotation_euler[0]
        for frame in (start_frame, total_frames):
            camera.location.z = base_z
            camera.keyframe_insert(data_path="location", frame=frame, index=2)
            camera.rotation_euler[0] = base_rot_x
            camera.keyframe_insert(data_path="rotation_euler", frame=frame, index=0)

        if hasattr(action, "fcurves"):
            fcurve_z = action.fcurves.find("location", index=2)
            fcurve_rot_x = action.fcurves.find("rotation_euler", index=0)
        else:
            fcurve_z = action.fcurve_ensure_for_datablock(camera, data_path="location", index=2)
            fcurve_rot_x = action.fcurve_ensure_for_datablock(camera, data_path="rotation_euler", index=0)

        if fcurve_z:
            mod_z = fcurve_z.modifiers.new(type="NOISE")
            mod_z.scale = 2.0
            mod_z.strength = 0.05

        if fcurve_rot_x:
            mod_rot = fcurve_rot_x.modifiers.new(type="NOISE")
            mod_rot.scale = 5.0
            mod_rot.strength = 0.002
