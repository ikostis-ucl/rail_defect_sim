from __future__ import annotations

import argparse
import sys
from dataclasses import replace

try:
    import configargparse
except ModuleNotFoundError:
    configargparse = None

from app.config import PipelineSettings


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
    parser.add_argument("--track-length", type=int, help="Track length override.")
    parser.add_argument(
        "--base-speed-units-per-frame",
        type=float,
        help="Base camera speed override in Blender units per frame.",
    )
    return parser


def _extract_script_args(argv: list[str] | None = None) -> list[str]:
    """Return only args intended for the Python script when run via Blender."""
    raw_args = list(sys.argv if argv is None else argv)
    if "--" in raw_args:
        return raw_args[raw_args.index("--") + 1 :]
    return raw_args[1:]


def parse_pipeline_settings(argv: list[str] | None = None) -> PipelineSettings:
    """Parse CLI/config-file arguments and map them to PipelineSettings."""
    parser = build_parser()
    args = parser.parse_args(_extract_script_args(argv))

    settings = PipelineSettings()

    updates = {
        "fps": args.fps,
        "duration_seconds": args.duration_seconds,
        "resolution_x": args.resolution_x,
        "resolution_y": args.resolution_y,
        "output_filename": args.output_filename,
        "render_engine": args.render_engine,
        "track_length": args.track_length,
        "base_speed_units_per_frame": args.base_speed_units_per_frame,
    }
    filtered_updates = {k: v for k, v in updates.items() if v is not None}

    if filtered_updates:
        settings = replace(settings, **filtered_updates)

    return settings
