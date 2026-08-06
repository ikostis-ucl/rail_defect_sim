"""CameraConfig — sensor geometry, field of view, footprint, height datum."""

import math

import pytest

from app.config import TrackGeometryConfig
from app.config.camera import CameraConfig, HeightReference


# ── Sensor geometry ───────────────────────────────────────────────────────────

def test_landscape_sensor_width_applies_to_wider_axis():
    """Mirrors Blender's sensor_fit='AUTO': the given width is the larger axis."""
    h, v = CameraConfig().sensor_dimensions_mm(960, 540)
    assert h == pytest.approx(36.0)
    assert v == pytest.approx(36.0 * 540 / 960)


def test_portrait_sensor_width_applies_to_taller_axis():
    h, v = CameraConfig().sensor_dimensions_mm(540, 960)
    assert v == pytest.approx(36.0)
    assert h == pytest.approx(36.0 * 540 / 960)


def test_square_aspect_is_symmetric():
    h, v = CameraConfig().sensor_dimensions_mm(512, 512)
    assert h == pytest.approx(v)


def test_zero_resolution_rejected():
    with pytest.raises(ValueError):
        CameraConfig().sensor_dimensions_mm(0, 540)


# ── Field of view ─────────────────────────────────────────────────────────────

def test_fov_matches_the_standard_formula():
    cfg = CameraConfig(lens_mm=35.0)
    h_fov, v_fov = cfg.fov_deg(960, 540)
    assert h_fov == pytest.approx(math.degrees(2 * math.atan(36.0 / 70.0)))
    assert h_fov == pytest.approx(54.43, abs=0.01)
    assert v_fov < h_fov


def test_shorter_lens_widens_the_view():
    wide = CameraConfig(lens_mm=24.0).fov_deg(960, 540)[0]
    tele = CameraConfig(lens_mm=85.0).fov_deg(960, 540)[0]
    assert wide > tele


# ── Footprint ─────────────────────────────────────────────────────────────────

def test_footprint_equals_the_trigonometric_form():
    """distance * sensor / lens is exactly 2*d*tan(fov/2), without the trig."""
    cfg = CameraConfig(lens_mm=35.0)
    distance = 2.45
    width, depth = cfg.footprint(distance, 960, 540)
    h_mm, v_mm = cfg.sensor_dimensions_mm(960, 540)
    assert width == pytest.approx(2 * distance * math.tan(math.atan(h_mm / (2 * 35.0))))
    assert depth == pytest.approx(2 * distance * math.tan(math.atan(v_mm / (2 * 35.0))))


def test_birds_eye_default_footprint_is_known():
    """Regression guard on the documented 2.52 m x 1.42 m bird's-eye frame."""
    width, depth = CameraConfig(height=2.45, lens_mm=35.0).footprint(2.45, 960, 540)
    assert width == pytest.approx(2.52, abs=0.01)
    assert depth == pytest.approx(1.42, abs=0.01)


def test_footprint_scales_linearly_with_distance():
    cfg = CameraConfig()
    near = cfg.footprint(2.0, 960, 540)[1]
    far = cfg.footprint(6.0, 960, 540)[1]
    assert far == pytest.approx(3 * near)


def test_nonpositive_lens_rejected():
    with pytest.raises(ValueError):
        CameraConfig(lens_mm=0.0).footprint(2.0, 960, 540)


# ── Height datum ──────────────────────────────────────────────────────────────

def test_world_reference_ignores_geometry():
    cfg = CameraConfig(height=2.45, height_reference=HeightReference.WORLD)
    assert cfg.resolve_world_height(TrackGeometryConfig().rail_top_z) == 2.45


def test_rail_top_reference_adds_the_railhead_datum():
    geometry = TrackGeometryConfig()
    cfg = CameraConfig(height=1.0, height_reference=HeightReference.RAIL_TOP)
    assert cfg.resolve_world_height(geometry.rail_top_z) == pytest.approx(
        geometry.rail_top_z + 1.0
    )


def test_rail_top_reference_tracks_changing_geometry():
    """The whole point: clearance above the rail survives a geometry change."""
    cfg = CameraConfig(height=1.0, height_reference=HeightReference.RAIL_TOP)
    default = TrackGeometryConfig()
    shallower = TrackGeometryConfig(sleeper_height=0.130)

    assert default.rail_top_z != shallower.rail_top_z
    # Absolute Z differs, but clearance above the railhead is identical.
    assert cfg.resolve_world_height(default.rail_top_z) - default.rail_top_z == pytest.approx(1.0)
    assert cfg.resolve_world_height(shallower.rail_top_z) - shallower.rail_top_z == pytest.approx(1.0)


def test_unknown_height_reference_rejected():
    with pytest.raises(ValueError, match="height_reference"):
        CameraConfig(height_reference="orbit").resolve_world_height(0.5)


def test_config_is_frozen():
    with pytest.raises(Exception):
        CameraConfig().lens_mm = 50  # type: ignore[misc]


# ── HeightReference enum ──────────────────────────────────────────────────────

def test_height_reference_values():
    assert HeightReference.WORLD == "world"
    assert HeightReference.RAIL_TOP == "rail_top"


def test_height_reference_accepts_plain_strings_from_yaml():
    """StrEnum: a value loaded from YAML as a bare string still resolves."""
    cfg = CameraConfig(height=1.0, height_reference="rail_top")
    assert cfg.resolve_world_height(0.466) == pytest.approx(1.466)


def test_default_height_reference_is_world():
    assert CameraConfig().height_reference is HeightReference.WORLD
