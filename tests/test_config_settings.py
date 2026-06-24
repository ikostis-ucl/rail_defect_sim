import pytest
from app.config.settings import PipelineSettings


def test_default_fps():
    assert PipelineSettings().fps == 12


def test_default_duration():
    assert PipelineSettings().duration_seconds == 10


def test_default_resolution():
    s = PipelineSettings()
    assert s.resolution_x == 960
    assert s.resolution_y == 540


def test_default_render_engine():
    assert PipelineSettings().render_engine == "BLENDER_EEVEE"


def test_default_track_length():
    assert PipelineSettings().track_length == 100_000


def test_default_speed():
    assert PipelineSettings().base_speed_units_per_frame == 2.5


def test_total_frames():
    s = PipelineSettings(fps=24, duration_seconds=5)
    assert s.total_frames == 120


def test_total_frames_default():
    s = PipelineSettings()  # 12 fps * 10 s
    assert s.total_frames == 120


def test_run_name_strips_extension():
    s = PipelineSettings(output_filename="my_render.mp4")
    assert s.run_name == "my_render"


def test_run_name_stem_only():
    s = PipelineSettings(output_filename="video.mkv")
    assert "." not in s.run_name


def test_output_path_contains_run_name():
    s = PipelineSettings(output_filename="test_run.mp4")
    assert "test_run" in s.output_path


def test_frozen_rejects_mutation():
    s = PipelineSettings()
    with pytest.raises(Exception):  # FrozenInstanceError (dataclasses.FrozenInstanceError)
        s.fps = 99  # type: ignore[misc]


def test_custom_values_round_trip():
    s = PipelineSettings(fps=30, duration_seconds=60, resolution_x=1920, resolution_y=1080)
    assert s.fps == 30
    assert s.duration_seconds == 60
    assert s.total_frames == 1800
