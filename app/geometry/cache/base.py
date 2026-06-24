from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import bpy

from app.geometry.cache.fingerprint import source_fingerprint
from app.geometry.cache.manifest import CacheManifest


class SectionCacheBase:
    """Shared disk/memory cache machinery for track section collections.

    Cache validity is automatic: each cache fingerprints the source files that
    define its build logic (``source_paths``).  A change to any of those files
    changes the fingerprint, which marks previously cached assets as stale.
    Stale files are pruned on construction; valid ones are reused.

    Subclasses set ``KIND`` and ``SOURCE_PATHS`` and implement their own
    ``get_or_create_*`` and ``_build_collection`` methods.
    """

    KIND: str = "section"
    SOURCE_PATHS: tuple[Path, ...] = ()

    def __init__(
        self,
        cache_dir: Path,
        *,
        source_paths: Iterable[Path] | None = None,
        auto_prune: bool = True,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.source_paths = tuple(
            source_paths if source_paths is not None else self.SOURCE_PATHS
        )
        self.fingerprint = source_fingerprint(self.source_paths)
        self.manifest = CacheManifest(self.cache_dir)
        if auto_prune:
            self._prune()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def _prune(self) -> None:
        removed = self.manifest.prune_stale(self.fingerprint)
        if removed:
            print(
                f"[{self.KIND} cache] pruned {len(removed)} stale asset(s) "
                f"(source changed; fingerprint now {self.fingerprint})"
            )
        # Keep the manifest in sync with disk: drop entries whose .blend was
        # deleted out-of-band so the inventory never claims a missing file.
        vanished = self.manifest.drop_missing_files()
        if vanished:
            print(
                f"[{self.KIND} cache] dropped {len(vanished)} manifest entr(ies) "
                f"whose .blend file no longer exists"
            )
        orphans = self.manifest.orphans()
        if orphans:
            preview = ", ".join(orphans[:3])
            suffix = ", ..." if len(orphans) > 3 else ""
            print(
                f"[{self.KIND} cache] {len(orphans)} unmanaged .blend file(s) "
                f"not in manifest (regenerable; safe to delete): {preview}{suffix}"
            )

    # ------------------------------------------------------------------
    # Shared get-or-create flow
    # ------------------------------------------------------------------

    def _get_or_create(
        self,
        *,
        collection_name: str,
        cache_key: str,
        params: dict[str, Any],
        build,
    ):
        """Return a cached collection or build, store, and record a new one.

        ``build(collection_name)`` must construct and return the collection.
        """
        cache_path = self.cache_dir / f"{collection_name}.blend"

        existing = bpy.data.collections.get(collection_name)
        if existing is not None:
            print(f"[{self.KIND} cache] hit (memory): {collection_name}")
            return existing

        if self.manifest.is_valid(collection_name, self.fingerprint) and cache_path.exists():
            loaded = self._load_collection(cache_path, collection_name)
            if loaded is not None and self._stamp_matches(loaded, cache_key):
                print(f"[{self.KIND} cache] hit (disk): {cache_path.name}")
                return loaded
            if loaded is not None:
                # Manifest said valid but the .blend's embedded provenance
                # disagrees (manifest/file divergence) — rebuild to be safe.
                print(
                    f"[{self.KIND} cache] stale stamp on {cache_path.name}; rebuilding"
                )

        print(f"[{self.KIND} cache] miss: building {collection_name}")
        collection = build(collection_name)
        created_at = datetime.now().isoformat(timespec="seconds")
        self._stamp(collection, cache_key=cache_key, params=params, created_at=created_at)
        self._write_collection(cache_path, collection)
        self.manifest.record(
            collection_name=collection_name,
            file_name=cache_path.name,
            kind=self.KIND,
            cache_key=cache_key,
            fingerprint=self.fingerprint,
            params=params,
            created_at=created_at,
        )
        print(f"[{self.KIND} cache] stored: {cache_path.name}")
        return collection

    def _stamp_matches(self, collection, cache_key: str) -> bool:
        """True if the loaded collection's embedded provenance is compatible.

        Defense-in-depth on top of the manifest check: verifies the fingerprint
        and key baked into the .blend itself match the current build, so a
        manifest/file divergence can't serve an incompatible collection.
        """
        return (
            collection.get("source_fingerprint") == self.fingerprint
            and collection.get("cache_key") == cache_key
        )

    def _stamp(
        self,
        collection,
        *,
        cache_key: str,
        params: dict[str, Any],
        created_at: str,
    ) -> None:
        """Embed provenance on the collection so the .blend is self-describing."""
        collection["cache_kind"] = self.KIND
        collection["cache_key"] = cache_key
        collection["source_fingerprint"] = self.fingerprint
        collection["cache_params"] = json.dumps(params, sort_keys=True)
        collection["created_at"] = created_at

    # ------------------------------------------------------------------
    # bpy I/O
    # ------------------------------------------------------------------

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
        # json.dumps with sort_keys=True handles nested dicts from RailConfig recursively.
        # default=str catches any non-serialisable stragglers.
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]
