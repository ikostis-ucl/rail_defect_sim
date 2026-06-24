"""Self-describing inventory of cached section assets.

A ``cache_index.json`` lives next to the ``.blend`` files in each cache
directory and records, for every cached collection, its provenance: the
geometry/defect parameters that produced it, the source fingerprint of the
build logic, and when it was created.  This makes the cache auditable at a
glance and lets stale entries be evicted deterministically.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class CacheManifest:
    """Reads, writes, and prunes the ``cache_index.json`` for one cache dir."""

    FILENAME = "cache_index.json"
    SCHEMA = 1

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.path = self.cache_dir / self.FILENAME
        self._entries: dict[str, dict[str, Any]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"Cache manifest unreadable, starting fresh: {self.path}")
            return
        if not isinstance(data, dict) or data.get("schema") != self.SCHEMA:
            print(
                f"Cache manifest schema mismatch "
                f"({data.get('schema') if isinstance(data, dict) else '?'} != {self.SCHEMA}); "
                f"starting fresh: {self.path}"
            )
            return
        for entry in data.get("entries", []):
            name = entry.get("collection_name")
            if name:
                self._entries[name] = entry

    def save(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": self.SCHEMA,
            "entries": sorted(
                self._entries.values(), key=lambda e: e["collection_name"]
            ),
        }
        # Per-process tmp name so concurrent writers don't clobber each other's
        # temp file; the final replace is atomic on the same filesystem.
        tmp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
        tmp.replace(self.path)  # atomic swap on the same filesystem

    # ------------------------------------------------------------------
    # Entries
    # ------------------------------------------------------------------

    def get(self, collection_name: str) -> dict[str, Any] | None:
        return self._entries.get(collection_name)

    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries.values())

    def record(
        self,
        *,
        collection_name: str,
        file_name: str,
        kind: str,
        cache_key: str,
        fingerprint: str,
        params: dict[str, Any],
        created_at: str,
    ) -> None:
        """Insert or replace the entry for *collection_name* and persist."""
        self._entries[collection_name] = {
            "collection_name": collection_name,
            "file": file_name,
            "kind": kind,
            "cache_key": cache_key,
            "source_fingerprint": fingerprint,
            "params": params,
            "created_at": created_at,
        }
        self.save()

    def is_valid(self, collection_name: str, fingerprint: str) -> bool:
        """True if *collection_name* is recorded with a matching fingerprint."""
        entry = self._entries.get(collection_name)
        return entry is not None and entry.get("source_fingerprint") == fingerprint

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def _resolve_blend(self, collection_name: str, entry: dict[str, Any]) -> Path | None:
        """Return the entry's .blend path, or None if its ``file`` is malformed.

        Guards against drifted/hand-edited entries: the file must be present and
        must be exactly ``<collection_name>.blend`` (the invariant ``record``
        maintains), so we never unlink the cache dir itself or an unrelated file.
        """
        file_name = entry.get("file")
        if not file_name or file_name != f"{collection_name}.blend":
            return None
        return self.cache_dir / file_name

    def prune_stale(self, current_fingerprint: str) -> list[str]:
        """Drop entries whose fingerprint != *current_fingerprint*.

        Deletes the backing ``.blend`` (when the entry's file is well-formed)
        and removes the manifest entry.  A malformed entry is dropped without
        touching disk.  Returns the names of the collections that were evicted.
        """
        removed: list[str] = []
        for name, entry in list(self._entries.items()):
            if entry.get("source_fingerprint") == current_fingerprint:
                continue
            blend = self._resolve_blend(name, entry)
            if blend is not None:
                try:
                    blend.unlink(missing_ok=True)
                except OSError as exc:
                    print(f"Could not remove stale cache file {blend}: {exc}")
            del self._entries[name]
            removed.append(name)
        if removed:
            self.save()
        return removed

    def drop_missing_files(self) -> list[str]:
        """Remove entries whose backing ``.blend`` is missing or malformed.

        Keeps the manifest in sync with disk when files are deleted out-of-band.
        Does not touch disk. Returns the names of the entries that were dropped.
        """
        removed: list[str] = []
        for name, entry in list(self._entries.items()):
            blend = self._resolve_blend(name, entry)
            if blend is not None and blend.exists():
                continue
            del self._entries[name]
            removed.append(name)
        if removed:
            self.save()
        return removed

    def orphans(self) -> list[str]:
        """Return ``.blend`` files on disk that the manifest doesn't track."""
        known = {entry.get("file") for entry in self._entries.values()}
        return sorted(
            p.name for p in self.cache_dir.glob("*.blend") if p.name not in known
        )
