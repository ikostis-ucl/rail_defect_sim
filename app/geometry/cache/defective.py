from __future__ import annotations

import json
from pathlib import Path

import bpy

from app.geometry.cache.base import SectionCacheBase
from app.geometry.track_section import TrackSection


class DefectiveSectionCache(SectionCacheBase):
    """Loads and stores reusable defective track section prototypes."""

    CACHE_VERSION = 6  # bumped: rail_angle field added to TrackGeometryConfig

    def __init__(self, cache_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        super().__init__(
            cache_dir or project_root / "assets" / "track_section_cache" / "defective"
        )

    def get_or_create_defective_collection(self, section: TrackSection, variant):
        """Return a cached defective section collection for *variant*."""
        payload = {
            "cache_version": self.CACHE_VERSION,
            "defect_name": variant.defect_name,
            **section.geometry_payload(),
            **variant.defect_params,
        }
        cache_key = self._make_cache_key(payload)
        collection_name = f"DefectiveSection_{variant.defect_name}_{cache_key}"
        cache_path = self.cache_dir / f"{collection_name}.blend"

        existing = bpy.data.collections.get(collection_name)
        if existing is not None:
            print(f"Defective section cache hit (memory): {collection_name}")
            return existing

        if cache_path.exists():
            loaded = self._load_collection(cache_path, collection_name)
            if loaded is not None:
                print(f"Defective section cache hit (disk): {cache_path.name}")
                return loaded

        print(f"Defective section cache miss: building {collection_name}")
        collection = self._build_collection(collection_name, section, variant)
        self._write_collection(cache_path, collection)
        print(f"Defective section cache stored: {cache_path}")
        return collection

    def _build_collection(self, collection_name: str, section: TrackSection, variant):
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)
        variant.apply(section)

        collection["cache_version"] = self.CACHE_VERSION
        collection["defect_name"] = variant.defect_name
        collection["defect_params"] = json.dumps(variant.defect_params, sort_keys=True)
        collection["track_section_geometry"] = json.dumps(
            section.geometry_payload(), sort_keys=True
        )
        return collection
