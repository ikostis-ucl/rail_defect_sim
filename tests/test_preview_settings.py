"""A preview is the same run, made cheap.

It exists so a user can look before committing to a full render. That only works
if it shows the *same shot* — same track, same viewpoint, same defects — so the
tests below are mostly about what a preview must **not** change.
"""

import pytest

from app.config import CameraConfig, PipelineSettings, RenderConfig, TrackGeometryConfig
from app.config.settings import PREVIEW_DURATION_S, PREVIEW_FPS, PREVIEW_HEIGHT


def full(**kw):
    return PipelineSettings(
        render=RenderConfig(resolution_x=1920, resolution_y=1080, fps=30, duration_seconds=60),
        **kw,
    )


# ── What a preview changes ────────────────────────────────────────────────────

def test_preview_is_small_short_and_coarse():
    p = full().preview()
    assert p.render.resolution_y == PREVIEW_HEIGHT
    assert p.render.duration_seconds == PREVIEW_DURATION_S
    assert p.render.fps == PREVIEW_FPS


def test_preview_keeps_the_aspect_ratio():
    """Framing must match, or the preview answers a different question."""
    p = full().preview()
    assert p.render.aspect_ratio == pytest.approx(16 / 9, abs=0.01)
    assert (p.render.resolution_x, p.render.resolution_y) == (568, 320)


@pytest.mark.parametrize(
    "width,height",
    [(1920, 1080), (3840, 2160), (960, 540), (1000, 1000), (1440, 1080)],
)
def test_preview_dimensions_are_even(width, height):
    """h264 refuses odd dimensions."""
    p = PipelineSettings(render=RenderConfig(resolution_x=width, resolution_y=height)).preview()
    assert p.render.resolution_x % 2 == 0
    assert p.render.resolution_y % 2 == 0


def test_preview_writes_to_its_own_file():
    p = PipelineSettings(output_filename="my_run.mp4").preview()
    assert p.output_filename == "my_run_preview.mp4"


# ── What a preview must not change ────────────────────────────────────────────

def test_preview_keeps_the_scene_identical():
    """Geometry, camera, speed, seed and defect placement all decide *what* is
    rendered. A preview that changed any of them would show a different track."""
    original = full(
        geometry=TrackGeometryConfig(profile="UIC60", rail_spacing=1.435),
        camera=CameraConfig(lens_mm=85, height=4.0),
        speed_kmh=120.0,
        seed=7,
        defect_rate=0.25,
        force_defect="skewed_sleeper",
    )
    p = original.preview()

    assert p.geometry == original.geometry
    assert p.camera == original.camera
    assert p.speed_kmh == original.speed_kmh
    assert p.seed == original.seed
    assert p.defect_rate == original.defect_rate
    assert p.force_defect == original.force_defect


def test_preview_covers_less_track_because_it_is_shorter():
    """Not a scene change: the camera moves at the same speed for less time."""
    original = full(speed_kmh=72.0)          # 20 m/s
    p = original.preview()
    assert p.speed_ms == original.speed_ms
    assert p.total_travel_distance_m == pytest.approx(60.0)   # 20 m/s x 3 s


def test_preview_leaves_the_original_untouched():
    original = full()
    original.preview()
    assert original.render.resolution_y == 1080
    assert original.render.duration_seconds == 60


# ── Never more expensive than the real thing ──────────────────────────────────

def test_preview_does_not_upscale_a_small_render():
    small = PipelineSettings(render=RenderConfig(resolution_x=320, resolution_y=180))
    p = small.preview()
    assert p.render.resolution_y == 180
    assert p.render.resolution_x == 320


def test_preview_does_not_lengthen_a_short_clip():
    brief = PipelineSettings(render=RenderConfig(duration_seconds=1))
    assert brief.preview().render.duration_seconds == 1


def test_preview_does_not_raise_a_low_frame_rate():
    coarse = PipelineSettings(render=RenderConfig(fps=5))
    assert coarse.preview().render.fps == 5


def test_preview_is_always_cheaper_or_equal():
    for x, y, fps, seconds in [
        (1920, 1080, 30, 60), (3840, 2160, 60, 120), (640, 360, 12, 10), (320, 240, 5, 2)
    ]:
        s = PipelineSettings(
            render=RenderConfig(resolution_x=x, resolution_y=y, fps=fps, duration_seconds=seconds)
        )
        p = s.preview()
        pixels_before = x * y * fps * seconds
        r = p.render
        pixels_after = r.resolution_x * r.resolution_y * r.fps * r.duration_seconds
        assert pixels_after <= pixels_before


def test_preview_is_idempotent():
    """Previewing a preview must not shrink it further."""
    once = full().preview()
    twice = once.preview()
    assert twice.render == once.render
