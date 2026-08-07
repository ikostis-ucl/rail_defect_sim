"""CLI argument mapping.

The CLI surface stays flat (``--camera-height``) because that is what users and
the ``configs/camera/*.yml`` presets write. These tests pin the folding of that
flat surface into the per-domain config objects.
"""

import pytest

from config import parse_pipeline_settings


def parse(*args):
    return parse_pipeline_settings(["--", *args])


# ── Defaults survive when nothing is passed ───────────────────────────────────

def test_no_args_yields_defaults():
    s = parse()
    assert s.render.fps == 12
    assert s.camera.lens_mm == 35.0
    assert s.seed == 42


def test_unrelated_flag_does_not_disturb_other_domains():
    """Setting a render value must not reset the camera to defaults."""
    s = parse("--fps", "30")
    assert s.render.fps == 30
    assert s.camera.height == 2.45
    assert s.camera.lens_mm == 35.0


# ── Render domain ─────────────────────────────────────────────────────────────

def test_render_flags_land_on_render_config():
    s = parse(
        "--fps", "24", "--duration-seconds", "5",
        "--resolution-x", "1920", "--resolution-y", "1080",
    )
    assert (s.render.fps, s.render.duration_seconds) == (24, 5)
    assert (s.render.resolution_x, s.render.resolution_y) == (1920, 1080)
    assert s.render.total_frames == 120


def test_render_engine_flag():
    assert parse("--render-engine", "CYCLES").render.engine == "CYCLES"


# ── Camera domain ─────────────────────────────────────────────────────────────

def test_camera_flags_land_on_camera_config():
    s = parse(
        "--camera-height", "6.0", "--camera-tilt-deg", "35",
        "--camera-lens", "85", "--camera-lateral-offset", "1.5",
        "--camera-yaw-deg", "10", "--camera-roll-deg", "2",
        "--camera-accel-seconds", "0",
    )
    c = s.camera
    assert c.height == 6.0
    assert c.tilt_deg == 35.0
    assert c.lens_mm == 85.0
    assert c.lateral_offset == 1.5
    assert c.yaw_deg == 10.0
    assert c.roll_deg == 2.0
    assert c.accel_seconds == 0.0


def test_sensor_width_is_settable():
    """Previously implicit in Blender; now an explicit, checkable value."""
    assert parse().camera.sensor_width_mm == 36.0
    assert parse("--camera-sensor-width", "23.5").camera.sensor_width_mm == 23.5


def test_height_reference_flag():
    assert parse().camera.height_reference == "world"
    assert parse("--camera-height-reference", "rail_top").camera.height_reference == "rail_top"


def test_invalid_height_reference_rejected(capsys):
    with pytest.raises(SystemExit):
        parse("--camera-height-reference", "orbit")


# ── Run-level values ──────────────────────────────────────────────────────────

def test_run_level_flags():
    s = parse(
        "--track-length-m", "500",
        "--speed-kmh", "36",
        "--output-filename", "clip.mp4",
        "--seed", "7",
        "--force-defect", "skewed_sleeper",
        "--geometry-config", "configs/geometry/wide_gauge.yml",
    )
    assert s.track_length_m == 500
    assert s.speed_kmh == 36
    assert s.output_filename == "clip.mp4"
    assert s.seed == 7
    assert s.force_defect == "skewed_sleeper"
    assert s.geometry_config_path == "configs/geometry/wide_gauge.yml"


def test_blender_argument_passthrough_is_stripped():
    """Everything before `--` belongs to Blender, not to us."""
    s = parse_pipeline_settings(["blender", "--background", "--", "--fps", "20"])
    assert s.render.fps == 20


def test_travel_distance_reflects_parsed_values():
    s = parse("--fps", "10", "--duration-seconds", "10", "--speed-kmh", "36")
    assert s.total_travel_distance_m == pytest.approx(100.0)


# ── Geometry resolution ───────────────────────────────────────────────────────

def test_geometry_defaults_when_no_file_given():
    from app.config import TrackGeometryConfig

    s = parse()
    assert s.geometry == TrackGeometryConfig()
    assert s.geometry_config_path is None


def test_geometry_file_is_resolved_at_parse_time():
    """Not just stored as a path — loaded, so validation can run pre-Blender."""
    s = parse("--geometry-config", "configs/geometry/wide_gauge.yml")
    assert s.geometry_config_path == "configs/geometry/wide_gauge.yml"
    assert s.geometry.rail_spacing == pytest.approx(1.520)
    assert s.geometry.profile == "UIC60"


def test_resolved_geometry_exposes_the_railhead_datum():
    """The value the camera datum needs, available before Blender starts."""
    default = parse().geometry.rail_top_z
    broad = parse("--geometry-config", "configs/geometry/wide_gauge.yml").geometry.rail_top_z
    assert default == pytest.approx(0.466)
    assert broad == pytest.approx(0.397)
