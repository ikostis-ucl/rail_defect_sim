from __future__ import annotations

import json
from pathlib import Path

import bpy

from app.geometry.cache.base import SectionCacheBase
from app.geometry.track_section import TrackSection


class TrackSectionCache(SectionCacheBase):
    """Loads and stores reusable modular track section prototypes."""

    CACHE_VERSION = 17  # bumped: TrackSection now uses TrackGeometryConfig; payload keys changed

    def __init__(self, cache_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[3]
        super().__init__(cache_dir or project_root / "assets" / "track_section_cache")

    def get_or_create_prototype_collection(self, section: TrackSection):
        """Return a cached prototype collection for *section*'s geometry."""
        payload = {"cache_version": self.CACHE_VERSION, **section.geometry_payload()}
        cache_key = self._make_cache_key(payload)
        collection_name = f"TrackSectionPrototype_{cache_key}"
        cache_path = self.cache_dir / f"{collection_name}.blend"

        existing = bpy.data.collections.get(collection_name)
        if existing is not None:
            print(f"Track section cache hit (memory): {collection_name}")
            return existing

        if cache_path.exists():
            loaded = self._load_collection(cache_path, collection_name)
            if loaded is not None:
                print(f"Track section cache hit (disk): {cache_path.name}")
                return loaded

        print(f"Track section cache miss: building {collection_name}")
        collection = self._build_collection(collection_name, section)
        self._write_collection(cache_path, collection)
        print(f"Track section cache stored: {cache_path}")
        return collection

    def _build_collection(self, collection_name: str, section: TrackSection):
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)
        collection["track_section_cache_version"] = self.CACHE_VERSION
        collection["track_section_geometry"] = json.dumps(
            section.geometry_payload(), sort_keys=True
        )
        return collection
