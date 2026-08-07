from __future__ import annotations

import argparse
import sys
from dataclasses import replace

try:
    import configargparse
except ModuleNotFoundError:
    configargparse = None

from app.config import PipelineSettings, TrackGeometryConfig
from app.config.camera import HeightReference


def build_parser() -> argparse.ArgumentParser:
    """Create a parser for pipeline runtime settings."""
    if configargparse is not None:
        parser: argparse.ArgumentParser = configargparse.ArgParser(
            description="Generate a railway flyover video in Blender.",
            auto_env_var_prefix="TSV_TWIN_",
            add_config_file_help=True,
        )
        parser.add_argument(
            "-c",
            "--config",
            is_config_file=True,
            help="Path to config file (yaml, ini, or key=value format).",
        )
    else:
        parser = argparse.ArgumentParser(
            description=(
                "Generate a railway flyover video in Blender. "
                "Install configargparse for --config and TSV_TWIN_* env support."
            )
        )

    parser.add_argument("--fps", type=int, help="Frames per second override.")
    parser.add_argument(
        "--duration-seconds",
        type=int,
        help="Duration override in seconds.",
    )
    parser.add_argument("--resolution-x", type=int, help="Horizontal resolution override.")
    parser.add_argument("--resolution-y", type=int, help="Vertical resolution override.")
    parser.add_argument(
        "--output-filename",
        type=str,
        help=(
            "Output video filename. Files are written under "
            "data/output/<filename_stem>/ by default."
        ),
    )
    parser.add_argument(
        "--render-engine",
        type=str,
        help="Blender render engine override (e.g. BLENDER_EEVEE).",
    )
    parser.add_argument(
        "--speed-kmh",
        type=float,
        help="Train speed in km/h. Frame rate does not affect it.",
    )
    parser.add_argument(
        "--track-length-m",
        type=float,
        help=(
            "Track length in metres. Omit to derive it from speed and duration, "
            "which is normally what you want."
        ),
    )
    parser.add_argument(
        "--track-length-km",
        type=float,
        help="Track length in kilometres. Convenience form of --track-length-m.",
    )
    parser.add_argument(
        "--geometry-config",
        type=str,
        dest="geometry_config",
        help=(
            "Path to a geometry .yml config file (e.g. configs/geometry/default.yml). "
            "Overrides built-in geometry defaults for rail, sleeper, and fastener dimensions."
        ),
    )
    parser.add_argument(
        "--force-defect",
        type=str,
        dest="force_defect",
        help=(
            "Force every section to use this defect type at 100%% probability. "
            "Useful for smoke tests. E.g. right_rail_lateral_displacement"
        ),
    )
    parser.add_argument(
        "--defect-rate",
        type=float,
        help=(
            "Fraction of sections that start a defect, 0.0-1.0. Default 0.10. "
            "Sets the balance of healthy to faulty examples in the dataset. "
            "Multi-section defects occupy follower sections too, so the share of "
            "defective sections ends up several times this value."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        help=(
            "RNG seed for defect placement. The same seed always produces the same "
            "sequence of defects along the track. Default 42; vary it to generate "
            "distinct datasets from otherwise identical settings."
        ),
    )
    parser.add_argument(
        "--camera-height",
        type=float,
        help="Camera height (Z) in metres. Default 2.45.",
    )
    parser.add_argument(
        "--camera-lateral-offset",
        type=float,
        help="Camera lateral offset (X) in metres; positive is right of track. Default 0.",
    )
    parser.add_argument(
        "--camera-tilt-deg",
        type=float,
        help="Camera tilt in degrees: 0 = straight down (bird's eye), 90 = looking forward. Default 0.",
    )
    parser.add_argument(
        "--camera-yaw-deg",
        type=float,
        help="Camera yaw in degrees: pan left/right about the vertical axis. Default 0.",
    )
    parser.add_argument(
        "--camera-roll-deg",
        type=float,
        help="Camera roll in degrees: bank about the view axis. Default 0.",
    )
    parser.add_argument(
        "--camera-lens",
        type=float,
        help="Camera focal length in mm (lower = wider FOV). Default 35.",
    )
    parser.add_argument(
        "--camera-sensor-width",
        type=float,
        help=(
            "Camera sensor width in mm. Default 36 (Blender's own default). "
            "Together with the lens this determines the field of view."
        ),
    )
    parser.add_argument(
        "--camera-height-reference",
        type=str,
        choices=[m.value for m in HeightReference],
        help=(
            "How --camera-height is interpreted: 'world' is an absolute Z "
            "coordinate (default); 'rail_top' is measured above the railhead, "
            "so the camera keeps its clearance when track geometry changes."
        ),
    )
    parser.add_argument(
        "--camera-accel-seconds",
        type=float,
        help="Ease-in ramp length in seconds before reaching cruising speed. "
             "0 = constant velocity (no acceleration). Default 10.",
    )
    return parser


def _extract_script_args(argv: list[str] | None = None) -> list[str]:
    """Return only args intended for the Python script when run via Blender."""
    raw_args = list(sys.argv if argv is None else argv)
    if "--" in raw_args:
        return raw_args[raw_args.index("--") + 1 :]
    return raw_args[1:]


def _track_length_override(args) -> float | None:
    """Resolve the track-length override from whichever unit was given.

    ``None`` means the user did not ask for a specific length, so it stays
    derived from speed and duration.
    """
    metres = getattr(args, "track_length_m", None)
    kilometres = getattr(args, "track_length_km", None)
    if metres is not None and kilometres is not None:
        raise SystemExit("Give --track-length-m or --track-length-km, not both.")
    if kilometres is not None:
        return kilometres * 1000.0
    return metres


def _override(config, **candidates):
    """Return *config* with only the non-None *candidates* applied."""
    provided = {k: v for k, v in candidates.items() if v is not None}
    return replace(config, **provided) if provided else config


def parse_pipeline_settings(argv: list[str] | None = None) -> PipelineSettings:
    """Parse CLI/config-file arguments and map them to PipelineSettings.

    The CLI surface stays flat (``--camera-height``, ``--fps``) because that is
    what users and the ``configs/camera/*.yml`` presets write. This function is
    the single place where that flat surface is folded into the per-domain
    config objects.
    """
    parser = build_parser()
    args = parser.parse_args(_extract_script_args(argv))

    defaults = PipelineSettings()

    render = _override(
        defaults.render,
        fps=args.fps,
        duration_seconds=args.duration_seconds,
        resolution_x=args.resolution_x,
        resolution_y=args.resolution_y,
        engine=args.render_engine,
    )

    camera = _override(
        defaults.camera,
        height=args.camera_height,
        height_reference=getattr(args, "camera_height_reference", None),
        lateral_offset=args.camera_lateral_offset,
        tilt_deg=args.camera_tilt_deg,
        yaw_deg=args.camera_yaw_deg,
        roll_deg=args.camera_roll_deg,
        lens_mm=args.camera_lens,
        sensor_width_mm=getattr(args, "camera_sensor_width", None),
        accel_seconds=args.camera_accel_seconds,
    )

    # Resolve the geometry file here rather than inside the pipeline, so a
    # complete run is fully described — and therefore validatable — before
    # Blender is ever launched.
    geometry_path = getattr(args, "geometry_config", None)
    geometry = (
        TrackGeometryConfig.from_yaml(geometry_path) if geometry_path else defaults.geometry
    )

    return _override(
        defaults,
        render=render,
        camera=camera,
        geometry=geometry,
        output_filename=args.output_filename,
        speed_kmh=getattr(args, "speed_kmh", None),
        track_length_override_m=_track_length_override(args),
        geometry_config_path=getattr(args, "geometry_config", None),
        force_defect=getattr(args, "force_defect", None),
        seed=args.seed,
        defect_rate=getattr(args, "defect_rate", None),
    )
