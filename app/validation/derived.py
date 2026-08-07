"""Quantities derived from *more than one* config.

Values belonging to a single config live on that config — ``rail_top_z`` on
``TrackGeometryConfig``, ``footprint()`` on ``CameraConfig``. What lives here is
everything that only exists once two configs are put side by side: how many
sections a track has, where the camera actually ends up, how much of the track
it sees, how long a defect is on the ground.

These are the quantities constraints are written against. Keeping them in one
place is what stops the same formula being recomputed slightly differently in
the builder, in a constraint, and in a YAML comment.

Nothing here imports ``bpy``.
"""

from __future__ import annotations

from app.config import PipelineSettings, TrackGeometryConfig

# ── Track extent ──────────────────────────────────────────────────────────────


def section_count(settings: PipelineSettings) -> int:
    """Number of track sections that will be built.

    Mirrors ``TrackBuilder.build()``. Drives build time and memory, so it is the
    quantity a render-budget check needs.
    """
    pitch = settings.geometry.section_pitch
    if pitch <= 0:
        return 0
    return int(settings.track_length_m / pitch) + 1


def track_build_length(settings: PipelineSettings) -> float:
    """Length of track actually built, in metres."""
    return float(settings.track_length_m)


# ── Camera placement ──────────────────────────────────────────────────────────


def camera_world_height(settings: PipelineSettings) -> float:
    """Absolute world Z the camera ends up at.

    Resolves ``CameraConfig.height`` against the active geometry, so a camera
    configured relative to the railhead reports where it will really sit.
    """
    return settings.camera.resolve_world_height(settings.geometry.rail_top_z)


def camera_height_above_rail(settings: PipelineSettings) -> float:
    """Clearance between the camera and the top of the rail, in metres.

    Negative means the camera is *below* the railhead — inside the track.
    """
    return camera_world_height(settings) - settings.geometry.rail_top_z


# ── What the camera sees ──────────────────────────────────────────────────────


def frame_footprint(settings: PipelineSettings) -> tuple[float, float]:
    """``(width, depth)`` in metres of ground visible in one frame.

    Measured at the camera's height above the rail, which is exact looking
    straight down. At a tilt the real ground footprint is a trapezoid running
    toward the horizon and this is the near-field approximation; the camera FOV
    constraints are where that distinction is handled properly.
    """
    return settings.camera.footprint(
        max(camera_height_above_rail(settings), 0.0),
        settings.render.resolution_x,
        settings.render.resolution_y,
    )


def sections_per_frame(settings: PipelineSettings) -> float:
    """How many sleeper bays fit in one frame along the track."""
    _, depth = frame_footprint(settings)
    pitch = settings.geometry.section_pitch
    return depth / pitch if pitch > 0 else 0.0


# ── Camera motion ─────────────────────────────────────────────────────────────


def frame_advance(settings: PipelineSettings) -> float:
    """Metres the camera travels between consecutive frames."""
    return settings.metres_per_frame


def frame_overlap_ratio(settings: PipelineSettings) -> float:
    """How much consecutive frames overlap along the track.

    ``1.0`` means each frame starts exactly where the previous ended — no
    overlap and no gap. Above 1 is overlap; **below 1 means track is skipped
    entirely and never imaged**.
    """
    advance = frame_advance(settings)
    if advance <= 0:
        return float("inf")
    _, depth = frame_footprint(settings)
    return depth / advance


def camera_travel_distance(settings: PipelineSettings) -> float:
    """Total distance the camera covers over the whole clip, in metres."""
    return settings.total_travel_distance_m


# ── Defect extent ─────────────────────────────────────────────────────────────


def defect_length(span_sections: int, geometry: TrackGeometryConfig) -> float:
    """Physical length of a defect spanning *span_sections* sections, in metres."""
    return span_sections * geometry.section_pitch


def longest_defect_length(settings: PipelineSettings) -> float:
    """Length of the longest defect that can occur, in metres.

    Read from the defect registry rather than hardcoded, so a new defect type
    with a longer span is accounted for without touching this function.
    """
    from app.geometry.defects.registry import ALL_DEFECTS

    longest = 0
    for defect_class in ALL_DEFECTS:
        for variant in defect_class.variants():
            longest = max(longest, defect_class.span_sections(variant.defect_params))
    return defect_length(longest, settings.geometry)


def smallest_defect_displacement(settings: PipelineSettings) -> float:
    """Smallest non-zero displacement any defect produces, in metres."""
    from app.geometry.defects.registry import ALL_DEFECTS

    magnitudes = [
        defect_class.displacement_m(variant.defect_params)
        for defect_class in ALL_DEFECTS
        for variant in defect_class.variants()
    ]
    non_zero = [m for m in magnitudes if m > 0]
    return min(non_zero) if non_zero else 0.0


def metres_per_pixel(settings: PipelineSettings) -> float:
    """Ground distance covered by one pixel across the frame width."""
    width, _ = frame_footprint(settings)
    return width / settings.render.resolution_x if settings.render.resolution_x else 0.0
