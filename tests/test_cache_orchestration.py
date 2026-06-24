"""Tests for SectionCacheBase orchestration: the get-or-create decision flow
and the prune/reconcile-on-construction behaviour.

bpy is a MagicMock (see conftest). We drive every branch by:
- patching bpy.data.collections.get to a dict (the "memory" cache), and
- subclassing SectionCacheBase to stub the .blend I/O hooks.
"""
from pathlib import Path
from unittest.mock import patch

import bpy  # MagicMock installed by conftest

from app.geometry.cache.base import SectionCacheBase


class _Coll(dict):
    """Dict-backed stand-in for a bpy collection (supports ['k'], .get, attrs)."""

    use_fake_user = False


def _memory(store):
    """Patch the in-memory collection lookup to consult *store* (name -> coll)."""
    return patch.object(bpy.data.collections, "get", side_effect=lambda n: store.get(n))


class FakeCache(SectionCacheBase):
    KIND = "fake"

    def __init__(self, cache_dir, *, loadable=None, auto_prune=True):
        self.build_calls = []
        self.loadable = loadable or {}  # name -> _Coll returned by _load_collection
        super().__init__(cache_dir, source_paths=[], auto_prune=auto_prune)

    def _build_collection(self, name):
        self.build_calls.append(name)
        return _Coll()

    def _write_collection(self, cache_path, collection):
        # Persist a real file so cache_path.exists() reflects writes.
        Path(cache_path).write_bytes(b"blend")

    def _load_collection(self, cache_path, collection_name):
        return self.loadable.get(collection_name)

    def make(self, name="Asset_k", key="k", params=None):
        return self._get_or_create(
            collection_name=name,
            cache_key=key,
            params=params or {"a": 1},
            build=self._build_collection,
        )


def test_miss_builds_writes_and_records(tmp_path):
    cache = FakeCache(tmp_path)
    with _memory({}):
        coll = cache.make(name="Asset_k", key="k")

    assert cache.build_calls == ["Asset_k"]
    assert (tmp_path / "Asset_k.blend").exists()
    entry = cache.manifest.get("Asset_k")
    assert entry is not None
    assert entry["source_fingerprint"] == cache.fingerprint
    assert entry["cache_key"] == "k"
    # Provenance is stamped on the collection itself.
    assert coll["source_fingerprint"] == cache.fingerprint
    assert coll["cache_key"] == "k"


def test_stamp_and_manifest_share_one_timestamp(tmp_path):
    cache = FakeCache(tmp_path)
    with _memory({}):
        coll = cache.make(name="Asset_k", key="k")
    # created_at must be computed once, not twice (no asset/manifest drift).
    assert coll["created_at"] == cache.manifest.get("Asset_k")["created_at"]


def test_memory_hit_skips_build(tmp_path):
    cache = FakeCache(tmp_path)
    sentinel = _Coll()
    with _memory({"Asset_k": sentinel}):
        coll = cache.make(name="Asset_k", key="k")
    assert coll is sentinel
    assert cache.build_calls == []


def test_disk_hit_loads_without_rebuild(tmp_path):
    # Seed a valid cached state.
    seed = FakeCache(tmp_path)
    with _memory({}):
        seed.make(name="Asset_k", key="k")

    # Fresh cache over the same dir: manifest persisted, file present.
    loaded = _Coll()
    cache2 = FakeCache(tmp_path, loadable={"Asset_k": loaded})
    loaded["source_fingerprint"] = cache2.fingerprint
    loaded["cache_key"] = "k"

    with _memory({}):
        coll = cache2.make(name="Asset_k", key="k")

    assert coll is loaded
    assert cache2.build_calls == []


def test_disk_stamp_mismatch_forces_rebuild(tmp_path):
    seed = FakeCache(tmp_path)
    with _memory({}):
        seed.make(name="Asset_k", key="k")

    loaded = _Coll()
    cache2 = FakeCache(tmp_path, loadable={"Asset_k": loaded}, auto_prune=False)
    loaded["source_fingerprint"] = "WRONG"  # manifest says valid, blend disagrees
    loaded["cache_key"] = "k"

    with _memory({}):
        cache2.make(name="Asset_k", key="k")

    assert cache2.build_calls == ["Asset_k"]


def test_valid_entry_but_missing_file_rebuilds(tmp_path):
    seed = FakeCache(tmp_path)
    with _memory({}):
        seed.make(name="Asset_k", key="k")
    (tmp_path / "Asset_k.blend").unlink()

    # auto_prune=False: the manifest still claims the now-missing file, so the
    # lookup-time `cache_path.exists()` guard is what must force the rebuild.
    cache2 = FakeCache(tmp_path, auto_prune=False)
    with _memory({}):
        cache2.make(name="Asset_k", key="k")

    assert cache2.build_calls == ["Asset_k"]


def test_prune_drops_entry_when_blend_deleted_out_of_band(tmp_path):
    seed = FakeCache(tmp_path)
    with _memory({}):
        seed.make(name="Asset_k", key="k")
    (tmp_path / "Asset_k.blend").unlink()

    # auto_prune on construction reconciles the manifest with disk.
    cache2 = FakeCache(tmp_path)
    assert cache2.manifest.get("Asset_k") is None


def test_prune_deletes_stale_fingerprint_file(tmp_path):
    cache = FakeCache(tmp_path)
    blend = tmp_path / "Old_x.blend"
    blend.write_bytes(b"x")
    cache.manifest.record(
        collection_name="Old_x",
        file_name="Old_x.blend",
        kind="fake",
        cache_key="x",
        fingerprint="STALE",  # != the FakeCache fingerprint
        params={},
        created_at="t",
    )

    FakeCache(tmp_path)  # auto_prune deletes the stale file + entry

    assert not blend.exists()
    assert FakeCache(tmp_path, auto_prune=False).manifest.get("Old_x") is None
