#!/usr/bin/env python3
"""Validate a run configuration without launching Blender.

Runs the same resolver the render entrypoint uses, so the two cannot disagree,
but in ordinary Python — it takes milliseconds instead of a Blender startup plus
a section-cache build.

Usage mirrors the render CLI exactly::

    python tools/preflight.py -- --camera-height 6 --geometry-config configs/geometry/wide_gauge.yml
    python tools/preflight.py -- --policy strict --fps 30
    python tools/preflight.py --json -- --speed-kmh 120

Exits 0 if the configuration is usable, 1 if it is not, so runtime scripts can
gate a render on it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.validation import Policy, Resolver  # noqa: E402
from app.validation.derived import (  # noqa: E402
    camera_height_above_rail,
    frame_footprint,
    frame_overlap_ratio,
    longest_defect_length,
    section_count,
)
from config import parse_pipeline_settings  # noqa: E402


def _extract_policy(argv: list[str]) -> tuple[Policy, list[str]]:
    """Pull ``--policy X`` out of the arguments; the rest go to the parser."""
    policy = Policy.REPAIR
    remaining: list[str] = []
    it = iter(argv)
    for arg in it:
        if arg == "--policy":
            policy = Policy(next(it, Policy.REPAIR))
        elif arg.startswith("--policy="):
            policy = Policy(arg.split("=", 1)[1])
        else:
            remaining.append(arg)
    return policy, remaining


def summarise(settings) -> str:
    """A short picture of what this configuration actually produces."""
    width, depth = frame_footprint(settings)
    return "\n".join(
        [
            "Configuration summary:",
            f"  train            {settings.speed_kmh:g} km/h "
            f"({settings.speed_ms:.1f} m/s), covering "
            f"{settings.total_travel_distance_m:.0f} m",
            f"  track            {settings.track_length_m:.0f} m"
            f"{'' if settings.track_length_override_m is not None else ' (derived)'}, "
            f"{section_count(settings)} sections at "
            f"{settings.geometry.section_pitch:g} m spacing",
            f"  geometry         {settings.geometry.profile}, gauge "
            f"{settings.geometry.rail_spacing:g} m, railhead at "
            f"{settings.geometry.rail_top_z:.3f} m",
            f"  camera           {camera_height_above_rail(settings):.3f} m above rail, "
            f"{settings.camera.lens_mm:g} mm lens",
            f"  frame covers     {width:.2f} m across x {depth:.2f} m along track",
            f"  frame overlap    {frame_overlap_ratio(settings):.2f}x "
            f"(below 1.0 means track is skipped)",
            f"  longest defect   {longest_defect_length(settings):.2f} m",
            f"  clip             {settings.render.total_frames} frames at "
            f"{settings.render.fps} fps, {settings.render.resolution_x}x"
            f"{settings.render.resolution_y}",
            f"  defects          {settings.defect_rate:.0%} start rate, seed {settings.seed}",
        ]
    )


def measurements(settings) -> dict:
    """The derived numbers, as data — the same ones ``summarise`` prints."""
    width, depth = frame_footprint(settings)
    return {
        "speed_kmh": settings.speed_kmh,
        "travel_distance_m": settings.total_travel_distance_m,
        "track_length_m": settings.track_length_m,
        "section_count": section_count(settings),
        "camera_height_above_rail_m": camera_height_above_rail(settings),
        "frame_width_m": width,
        "frame_depth_m": depth,
        "frame_overlap_ratio": frame_overlap_ratio(settings),
        "longest_defect_m": longest_defect_length(settings),
    }


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    # --json is ours, and is accepted on either side of the `--` separator.
    as_json = "--json" in raw
    raw = [a for a in raw if a != "--json"]
    if "--" in raw:
        raw = raw[raw.index("--") + 1 :]
    policy, args = _extract_policy(raw)

    settings = parse_pipeline_settings(["--", *args])
    report = Resolver(policy=policy).resolve(settings)

    if as_json:
        payload = report.as_dict()
        payload["measurements"] = measurements(report.settings)
        print(json.dumps(payload, indent=2))
    else:
        print(summarise(report.settings))
        print()
        print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
