from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bpy


class SectionCacheBase:
    """
    Shared disk/memory cache machinery for track section collections.

    Subclasses supply CACHE_VERSION and implement their own
    get_or_create_* and _build_collection methods.
    """

    CACHE_VERSION: int

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_collection(cache_path: Path, collection_name: str):
        with bpy.data.libraries.load(str(cache_path), link=False) as (data_from, data_to):
            data_to.collections = (
                [collection_name] if collection_name in data_from.collections else []
            )
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
    def _make_cache_key(payload: dict) -> str:
        hashable = {k: str(v) for k, v in payload.items()}
        encoded = json.dumps(hashable, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]
