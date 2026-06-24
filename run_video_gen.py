from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when Blender runs this file directly.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import PipelineSettings
from app.core import RailwayVideoPipeline
from config import parse_pipeline_settings


def run(
    settings: PipelineSettings | None = None,
) -> None:
    """Canonical application entrypoint for Blender and programmatic use."""
    if settings is None:
        settings = PipelineSettings()

    pipeline = RailwayVideoPipeline(settings)
    pipeline.run()


def main() -> None:
    """CLI entrypoint that always resolves settings from config.py."""
    run(settings=parse_pipeline_settings())


if __name__ == "__main__":
    main()
