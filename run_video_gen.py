from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when Blender runs this file directly.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import PipelineSettings
from app.core import RailwayVideoPipeline
from app.validation import resolve_or_raise
from config import parse_pipeline_settings


def run(
    settings: PipelineSettings | None = None,
    *,
    validate: bool = True,
) -> None:
    """Canonical application entrypoint for Blender and programmatic use.

    Settings are validated before the pipeline is built, so an impossible or
    useless configuration is caught before any geometry is generated. The same
    resolver runs in ``tools/preflight.py``, which gates a render without paying
    for Blender startup at all; this call is the safety net for direct
    ``blender --background --python`` invocations.
    """
    if settings is None:
        settings = PipelineSettings()

    if validate:
        settings = resolve_or_raise(settings)

    pipeline = RailwayVideoPipeline(settings)
    pipeline.run()


def main() -> None:
    """CLI entrypoint that always resolves settings from config.py."""
    run(settings=parse_pipeline_settings())


if __name__ == "__main__":
    main()
