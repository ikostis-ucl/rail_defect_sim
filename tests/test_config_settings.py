"""PipelineSettings as a composition root over the per-domain configs."""

from pathlib import Path

import pytest

from app.config import (
    AppearanceConfig,
    CameraConfig,
    EnvironmentConfig,
    PipelineSettings,
    RenderConfig,
)


# ── Composition ───────────────────────────────────────────────────────────────

def test_owns_one_config_per_domain():
    s = PipelineSettings()
    assert isinstance(s.render, RenderConfig)
    assert isinstance(s.camera, CameraConfig)
    assert isinstance(s.environment, EnvironmentConfig)
    assert isinstance(s.appearance, AppearanceConfig)


def test_domain_configs_are_independent_instances():
    """Mutable defaults must not be shared between PipelineSettings objects."""
    a, b = PipelineSettings(), PipelineSettings()
    assert a.render is not b.render
    assert a.camera is not b.camera
    assert a.environment is not b.environment


# ── Render defaults ───────────────────────────────────────────────────────────

def test_default_render_values():
    r = PipelineSettings().render
    assert r.fps == 12
    assert r.duration_seconds == 10
    assert r.resolution_x == 960
    assert r.resolution_y == 540
    assert r.engine == "BLENDER_EEVEE"
    assert r.start_frame == 1


def test_total_frames_derived_from_render_config():
    s = PipelineSettings(render=RenderConfig(fps=24, duration_seconds=5))
    assert s.render.total_frames == 120
    assert s.total_frames == 120  # exposed on settings for convenience


def test_total_frames_default():
    assert PipelineSettings().total_frames == 120  # 12 fps * 10 s


def test_aspect_ratio():
    assert RenderConfig(resolution_x=1920, resolution_y=1080).aspect_ratio == pytest.approx(16 / 9)


# ── Run-level values ──────────────────────────────────────────────────────────

def test_default_track_length():
    assert PipelineSettings().track_length == 100_000


def test_default_speed():
    assert PipelineSettings().base_speed_units_per_frame == 2.5


def test_default_seed_is_42():
    assert PipelineSettings().seed == 42


def test_total_travel_distance():
    """Distance covered over the clip — compared against track_length."""
    s = PipelineSettings(
        render=RenderConfig(fps=10, duration_seconds=10),  # 100 frames
        base_speed_units_per_frame=2.5,
    )
    assert s.total_travel_distance == pytest.approx(250.0)


# ── Output naming ─────────────────────────────────────────────────────────────

def test_run_name_strips_extension():
    assert PipelineSettings(output_filename="my_render.mp4").run_name == "my_render"


def test_run_name_stem_only():
    assert "." not in PipelineSettings(output_filename="video.mkv").run_name


def test_output_path_contains_run_name():
    assert "test_run" in PipelineSettings(output_filename="test_run.mp4").output_path


# ── Immutability ──────────────────────────────────────────────────────────────

def test_frozen_rejects_mutation():
    s = PipelineSettings()
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
        s.track_length = 99  # type: ignore[misc]


def test_domain_configs_are_frozen():
    s = PipelineSettings()
    with pytest.raises(Exception):
        s.render.fps = 99  # type: ignore[misc]
    with pytest.raises(Exception):
        s.camera.lens_mm = 99  # type: ignore[misc]


def test_custom_values_round_trip():
    s = PipelineSettings(
        render=RenderConfig(fps=30, duration_seconds=60, resolution_x=1920, resolution_y=1080)
    )
    assert s.render.fps == 30
    assert s.render.total_frames == 1800


# ── Geometry is resolved config, not a path ───────────────────────────────────

def test_geometry_is_a_resolved_config_object():
    """Every domain has its config on settings — geometry included.

    It used to be only a path, resolved inside RailwayVideoPipeline, which meant
    a run could not be fully described before Blender launched.
    """
    from app.config import TrackGeometryConfig

    s = PipelineSettings()
    assert isinstance(s.geometry, TrackGeometryConfig)
    assert s.geometry_config_path is None  # provenance only


def test_geometry_derived_values_reachable_from_settings():
    """The railhead datum the camera needs is available without Blender."""
    assert PipelineSettings().geometry.rail_top_z == pytest.approx(0.466)


# ── output_path purity ────────────────────────────────────────────────────────

def test_output_path_does_not_touch_the_filesystem():
    """Reading a config value must never create directories.

    Pre-render validation inspects these settings; if reading the path created
    the directory, every rejected run would still litter data/output/.
    """
    s = PipelineSettings(output_filename="never_rendered_probe_run.mp4")
    if s.output_dir.exists():                     # left over from an earlier run
        s.output_dir.rmdir()
    _ = s.output_path
    _ = s.output_dir
    assert not s.output_dir.exists()


def test_ensure_output_dir_creates_it_and_is_idempotent():
    s = PipelineSettings(output_filename="ensure_probe_run.mp4")
    try:
        created = s.ensure_output_dir()
        assert created.is_dir()
        assert s.ensure_output_dir() == created   # safe to call twice
    finally:
        if s.output_dir.exists():
            s.output_dir.rmdir()


def test_output_path_sits_inside_output_dir():
    s = PipelineSettings(output_filename="somewhere.mp4")
    assert Path(s.output_path).parent == s.output_dir
