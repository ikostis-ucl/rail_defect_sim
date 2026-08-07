"""Every consumer of speed and track length reads the metric quantities.

These exist because renaming the run-level fields broke the camera animator and
nothing caught it: the animator is the only consumer that needs ``bpy``, so no
test touched it and the failure only appeared in a real Blender run. The unit
tests below stand in for that render.
"""

import pytest

from app.config import PipelineSettings, RenderConfig, TrackGeometryConfig
from app.validation.derived import (
    camera_travel_distance,
    frame_advance,
    section_count,
    track_build_length,
)


# ── The user-facing statement ─────────────────────────────────────────────────

def test_a_train_at_100kmh_for_20_seconds():
    """The whole point: state the run in real units and nothing else."""
    s = PipelineSettings(speed_kmh=100.0, render=RenderConfig(duration_seconds=20))
    assert s.speed_ms == pytest.approx(27.778, abs=1e-3)
    assert s.total_travel_distance_m == pytest.approx(555.6, abs=0.1)
    assert s.track_length_m == pytest.approx(611.1, abs=0.1)   # +10 % margin


# ── The bug this replaced ─────────────────────────────────────────────────────

@pytest.mark.parametrize("fps", [5, 12, 25, 30, 60])
def test_frame_rate_never_changes_physical_speed(fps):
    s = PipelineSettings(speed_kmh=100.0, render=RenderConfig(fps=fps, duration_seconds=10))
    assert s.speed_kmh == 100.0
    assert s.speed_ms == pytest.approx(27.778, abs=1e-3)
    assert s.total_travel_distance_m == pytest.approx(277.8, abs=0.1)


def test_frame_rate_changes_only_the_sampling():
    coarse = PipelineSettings(render=RenderConfig(fps=10))
    fine = PipelineSettings(render=RenderConfig(fps=30))
    assert fine.metres_per_frame == pytest.approx(coarse.metres_per_frame / 3)


def test_zero_fps_does_not_divide_by_zero():
    assert PipelineSettings(render=RenderConfig(fps=0)).metres_per_frame == 0.0


# ── Consumers ─────────────────────────────────────────────────────────────────

def test_camera_animator_travels_the_derived_distance():
    """The reader that a rename broke, with bpy stubbed by conftest."""
    from app.camera import CameraAnimator

    s = PipelineSettings(speed_kmh=36.0, render=RenderConfig(duration_seconds=10))
    assert CameraAnimator(s).settings.total_travel_distance_m == pytest.approx(100.0)


def test_derived_quantities_read_the_metric_fields():
    s = PipelineSettings(speed_kmh=36.0, render=RenderConfig(fps=10, duration_seconds=10))
    assert frame_advance(s) == pytest.approx(1.0)             # 10 m/s / 10 fps
    assert camera_travel_distance(s) == pytest.approx(100.0)
    assert track_build_length(s) == pytest.approx(110.0)


def test_section_count_follows_the_derived_track_length():
    s = PipelineSettings(
        speed_kmh=36.0,
        render=RenderConfig(duration_seconds=10),
        geometry=TrackGeometryConfig(section_pitch=1.0),
    )
    assert section_count(s) == 111   # 110 m of track at 1 m pitch, plus the last


# ── Track length ──────────────────────────────────────────────────────────────

def test_track_always_outlasts_the_clip_when_derived():
    for kmh in (1, 25, 100, 350):
        for seconds in (1, 10, 60):
            s = PipelineSettings(speed_kmh=kmh, render=RenderConfig(duration_seconds=seconds))
            assert s.track_length_m > s.total_travel_distance_m


def test_override_is_taken_literally_even_when_too_short():
    """An explicit length is the user's call — deriving is what protects them."""
    s = PipelineSettings(
        speed_kmh=100.0, render=RenderConfig(duration_seconds=60),
        track_length_override_m=10.0,
    )
    assert s.track_length_m == 10.0
    assert s.total_travel_distance_m > s.track_length_m
