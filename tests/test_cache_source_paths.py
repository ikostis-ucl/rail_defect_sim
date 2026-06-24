"""Guard against the fingerprint's hand-maintained source list drifting.

The cache fingerprint only covers files listed in each cache's SOURCE_PATHS. If
TrackSection.build() grows a new ``app.geometry.*`` dependency that isn't listed,
edits to it would be silently served from a stale cache. These tests fail loudly
when that happens.
"""
import re
from pathlib import Path

from app.geometry.cache.prototype import TrackSectionCache
from app.geometry.cache.defective import DefectiveSectionCache

_GEOM_DIR = Path(__file__).resolve().parents[1] / "app" / "geometry"


def _imported_geometry_modules() -> set[str]:
    """Module names imported as ``from app.geometry.X import ...`` by track_section."""
    text = (_GEOM_DIR / "track_section.py").read_text(encoding="utf-8")
    return set(re.findall(r"from app\.geometry\.(\w+) import", text))


def _source_names(cache_cls) -> set[str]:
    return {Path(p).name for p in cache_cls.SOURCE_PATHS}


def test_track_section_imports_are_covered_by_both_caches():
    modules = _imported_geometry_modules()
    # Sanity: the helpers we explicitly added must be detected.
    assert {"layout", "utils"} <= modules

    for cache_cls in (TrackSectionCache, DefectiveSectionCache):
        names = _source_names(cache_cls)
        missing = {f"{m}.py" for m in modules} - names
        assert not missing, (
            f"{cache_cls.__name__}.SOURCE_PATHS is missing build dependencies "
            f"{missing}; add them or edits there won't invalidate the cache."
        )


def test_both_caches_include_track_section_itself():
    for cache_cls in (TrackSectionCache, DefectiveSectionCache):
        assert "track_section.py" in _source_names(cache_cls)


def test_all_source_paths_exist_on_disk():
    for cache_cls in (TrackSectionCache, DefectiveSectionCache):
        for p in cache_cls.SOURCE_PATHS:
            assert Path(p).exists(), f"{cache_cls.__name__} lists non-existent {p}"
