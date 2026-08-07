from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when Blender runs this file directly.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import PipelineSettings
from app.core import RailwayVideoPipeline
from app.progress import Cancelled, build_reporter, set_verbose
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

    set_verbose(settings.verbose)
    reporter = build_reporter(settings.progress_file, quiet=settings.quiet)
    try:
        RailwayVideoPipeline(settings, reporter=reporter).run()
    except Cancelled:
        # Not an error: the user asked for this. A distinct exit status lets a
        # caller tell "stopped on request" from "went wrong".
        raise SystemExit(130)
    finally:
        reporter.close()


def main() -> None:
    """CLI entrypoint that always resolves settings from config.py."""
    import sys as _sys

    settings = parse_pipeline_settings()
    if "--preview" in _sys.argv:
        settings = settings.preview()
    run(settings=settings)


if __name__ == "__main__":
    main()
