"""PipelineSettings as a composition root over the per-domain configs."""

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
