from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy

from app.geometry.track_section import TrackSection


class TrackSectionCache:
    """Loads and stores reusable modular track section prototypes."""

    CACHE_VERSION = 15

    def __init__(self, cache_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.cache_dir = cache_dir or project_root / "assets" / "track_section_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_or_create_prototype_collection(self, section: TrackSection):
        """Return a cached prototype collection for the provided section geometry."""
        payload = {
            "cache_version": self.CACHE_VERSION,
            **section.geometry_payload(),
        }
        cache_key = self._make_cache_key(payload)
        collection_name = f"TrackSectionPrototype_{cache_key}"
        cache_path = self.cache_dir / f"{collection_name}.blend"

        existing_collection = bpy.data.collections.get(collection_name)
        if existing_collection is not None:
            print(f"Track section cache hit (memory): {collection_name}")
            return existing_collection

        if cache_path.exists():
            loaded_collection = self._load_collection(cache_path, collection_name)
            if loaded_collection is not None:
                print(f"Track section cache hit (disk): {cache_path.name}")
                return loaded_collection

        print(f"Track section cache miss: building {collection_name}")
        prototype_collection = self._build_collection(collection_name, section)
        self._write_collection(cache_path, prototype_collection)
        print(f"Track section cache stored: {cache_path}")
        return prototype_collection

    def _build_collection(self, collection_name: str, section: TrackSection):
        collection = bpy.data.collections.new(collection_name)
        collection.use_fake_user = True
        section.build(location=(0, 0, 0), target_collection=collection)
        collection["track_section_cache_version"] = self.CACHE_VERSION
        collection["track_section_geometry"] = json.dumps(section.geometry_payload(), sort_keys=True)
        return collection

    @staticmethod
    def _load_collection(cache_path: Path, collection_name: str):
        with bpy.data.libraries.load(str(cache_path), link=False) as (data_from, data_to):
            data_to.collections = [collection_name] if collection_name in data_from.collections else []

        if not data_to.collections:
            return None

        collection = data_to.collections[0]
        if collection is not None:
            collection.use_fake_user = True
        return collection

    @staticmethod
    def _write_collection(cache_path: Path, collection) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.data.libraries.write(str(cache_path), {collection})

    @staticmethod
    def _make_cache_key(payload: dict[str, float | int]) -> str:
        encoded_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded_payload).hexdigest()[:16]
