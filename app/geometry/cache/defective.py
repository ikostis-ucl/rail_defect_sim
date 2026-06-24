from __future__ import annotations

from pathlib import Path

import bpy

from app.geometry.cache.base import SectionCacheBase
from app.geometry.track_section import TrackSection

_GEOM_DIR = Path(__file__).resolve().parents[1]  # app/geometry

# A defective section is a healthy section plus a defect mutation, so its build
# logic depends on the prototype sources (incl. the geometry helpers
# TrackSection.build imports) *and* every defect module.  rglob recurses into
# the per-defect subpackages (e.g. defects/rail_displacement/), so new defect
# files anywhere under defects/ are picked up automatically.
# test_cache_source_paths.py guards that build dependencies stay listed here.
_SOURCE_FILES = (
    _GEOM_DIR / "track_section.py",
    _GEOM_DIR / "layout.py",
    _GEOM_DIR / "utils.py",
    _GEOM_DIR / "cache" / "base.py",
    _GEOM_DIR / "cache" / "defective.py",
    *sorted((_GEOM_DIR / "defects").rglob("*.py")),
)


class DefectiveSectionCache(SectionCacheBase):
    """Loads and stores reusable defective track section prototypes."""

    KIND = "defective"
    SOURCE_PATHS = _SOURCE_FILES
    CACHE_VERSION = 8

    def __init__(self, cache_dir: Path | None = None, *, auto_prune: bool = True) -> None:
        project_root = Path(__file__).resolve().parents[3]
        super().__init__(
            cache_dir or project_root / "assets" / "track_section_cache" / "defective",
            auto_prune=auto_prune,
        )

    def get_or_create_defective_collection(self, section: TrackSection, variant):
        """Return a cached defective section collection for *variant*."""
        params = {
            "defect_name": variant.defect_name,
            **section.geometry_payload(),
            **variant.defect_params,
        }
        cache_key = self._make_cache_key(params)
        collection_name = f"DefectiveSection_{variant.defect_name}_{cache_key}"

        return self._get_or_create(
            collection_name=collection_name,
            cache_key=cache_key,
            params=params,
            build=lambda name: self._build_collection(name, section, variant),
        )

    def _build_collection(self, collection_name: str, section: TrackSection, variant):
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)
        variant.apply(section)
        return collection
