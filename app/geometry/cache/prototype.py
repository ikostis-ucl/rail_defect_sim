from __future__ import annotations

from pathlib import Path

import bpy

from app.geometry.cache.base import SectionCacheBase
from app.geometry.track_section import TrackSection

_GEOM_DIR = Path(__file__).resolve().parents[1]  # app/geometry

# Source files whose contents define how a healthy prototype is built.
# A change to any of these changes the fingerprint and invalidates old caches.
# This must cover every module TrackSection.build() depends on — including the
# geometry helpers it imports (layout, utils) — or an edit there would be
# silently served from a stale cache. test_cache_source_paths.py guards this.
_SOURCE_FILES = (
    _GEOM_DIR / "track_section.py",
    _GEOM_DIR / "layout.py",
    _GEOM_DIR / "utils.py",
    _GEOM_DIR / "cache" / "base.py",
    _GEOM_DIR / "cache" / "prototype.py",
)


class TrackSectionCache(SectionCacheBase):
    """Loads and stores reusable modular track section prototypes."""

    KIND = "prototype"
    SOURCE_PATHS = _SOURCE_FILES

    def __init__(self, cache_dir: Path | None = None, *, auto_prune: bool = True) -> None:
        project_root = Path(__file__).resolve().parents[3]
        super().__init__(
            cache_dir or project_root / "assets" / "track_section_cache",
            auto_prune=auto_prune,
        )

    def get_or_create_prototype_collection(self, section: TrackSection):
        """Return a cached prototype collection for *section*'s geometry."""
        params = section.geometry_payload()
        cache_key = self._make_cache_key(params)
        collection_name = f"TrackSectionPrototype_{cache_key}"

        return self._get_or_create(
            collection_name=collection_name,
            cache_key=cache_key,
            params=params,
            build=lambda name: self._build_collection(name, section),
        )

    def _build_collection(self, collection_name: str, section: TrackSection):
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)
        return collection
