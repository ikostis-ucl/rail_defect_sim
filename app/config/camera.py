"""
Camera configuration — pose, optics, and sensor.

This is the *data* half of the camera. The *builder* half is
``app.camera.CameraAnimator``, which turns this description into a Blender
camera object. Nothing here imports ``bpy``, so a camera can be described,
validated, and reasoned about without launching Blender.

All distances are in metres, angles in degrees, focal length and sensor in
millimetres.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Blender's default sensor width. It is never set explicitly by the pipeline,
# so every field-of-view calculation implicitly depends on this value; making
# it a real field is what allows FOV to be checked before a render.
DEFAULT_SENSOR_WIDTH_MM = 36.0

WORLD = "world"
RAIL_TOP = "rail_top"


@dataclass(frozen=True)
class CameraConfig:
    """Complete description of a camera's placement and optics.

    ``height_reference`` decides how ``height`` is interpreted:

      ``world``     — height is an absolute world-Z coordinate (legacy behaviour).
      ``rail_top``  — height is measured *above the top of the rail*, and the
                      absolute Z is derived from the active track geometry at
                      setup time.

    ``rail_top`` is the meaningful frame of reference for a real inspection
    camera: a cab window sits a fixed distance above the railhead regardless of
    sleeper height or rail profile. With ``world``, changing the track geometry
    silently moves the camera relative to the track.
    """

    # ── Placement ─────────────────────────────────────────────────────────────
    height: float = 2.45                 # see height_reference
    height_reference: str = WORLD
    lateral_offset: float = 0.0          # X; positive is right of track centre

    # ── Orientation ───────────────────────────────────────────────────────────
    tilt_deg: float = 0.0                # about X: 0 = straight down, 90 = forward
    yaw_deg: float = 0.0                 # about world Z: pan left/right
    roll_deg: float = 0.0                # about the view axis: bank

    # ── Optics ────────────────────────────────────────────────────────────────
    lens_mm: float = 35.0                # focal length; lower = wider FOV
    sensor_width_mm: float = DEFAULT_SENSOR_WIDTH_MM

    # ── Motion ────────────────────────────────────────────────────────────────
    accel_seconds: float = 10.0          # ease-in ramp; 0 = constant velocity

    # ── Sensor geometry ───────────────────────────────────────────────────────

    def sensor_dimensions_mm(
        self, resolution_x: int, resolution_y: int
    ) -> tuple[float, float]:
        """Return ``(horizontal_mm, vertical_mm)`` for the given image aspect.

        Mirrors Blender's ``sensor_fit = 'AUTO'`` rule: the configured sensor
        width applies to the *larger* image dimension, and the other dimension
        is scaled by the aspect ratio.
        """
        if resolution_x <= 0 or resolution_y <= 0:
            raise ValueError("resolution must be positive in both axes")
        if resolution_x >= resolution_y:
            horizontal = self.sensor_width_mm
            vertical = self.sensor_width_mm * resolution_y / resolution_x
        else:
            vertical = self.sensor_width_mm
            horizontal = self.sensor_width_mm * resolution_x / resolution_y
        return horizontal, vertical

    # ── Field of view ─────────────────────────────────────────────────────────

    def fov_deg(self, resolution_x: int, resolution_y: int) -> tuple[float, float]:
        """Return ``(horizontal_fov, vertical_fov)`` in degrees."""
        h_mm, v_mm = self.sensor_dimensions_mm(resolution_x, resolution_y)
        return (
            math.degrees(2 * math.atan(h_mm / (2 * self.lens_mm))),
            math.degrees(2 * math.atan(v_mm / (2 * self.lens_mm))),
        )

    def footprint(
        self, distance: float, resolution_x: int, resolution_y: int
    ) -> tuple[float, float]:
        """Return the ``(width, depth)`` in metres visible at *distance* metres.

        Derived from similar triangles rather than trigonometry: since
        ``tan(atan(y)) == y``, the usual ``2 * d * tan(fov / 2)`` collapses to

            extent = distance * sensor_mm / lens_mm

        which is exact and avoids a round trip through trig functions.

        This is the footprint on a plane *perpendicular to the view axis*. It is
        the true ground footprint only when looking straight down
        (``tilt_deg == 0``); at other tilts the ground footprint is a trapezoid
        and this value describes the frame at the given distance along the view
        axis, not along the ground.
        """
        if self.lens_mm <= 0:
            raise ValueError("lens_mm must be positive")
        h_mm, v_mm = self.sensor_dimensions_mm(resolution_x, resolution_y)
        return (distance * h_mm / self.lens_mm, distance * v_mm / self.lens_mm)

    # ── Height resolution ─────────────────────────────────────────────────────

    def resolve_world_height(self, rail_top_z: float) -> float:
        """Return the absolute world-Z for this camera.

        With ``height_reference == 'rail_top'`` the configured height is an
        offset above the railhead and *rail_top_z* is added to it. With
        ``'world'`` the configured height is already absolute and is returned
        unchanged.
        """
        if self.height_reference == RAIL_TOP:
            return rail_top_z + self.height
        if self.height_reference == WORLD:
            return self.height
        raise ValueError(
            f"Unknown height_reference {self.height_reference!r}; "
            f"expected {WORLD!r} or {RAIL_TOP!r}"
        )
