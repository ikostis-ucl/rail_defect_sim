"""Tests for CacheManifest (pure JSON inventory logic, no bpy calls)."""
import json

from app.geometry.cache.manifest import CacheManifest


def _record(manifest, name, fingerprint="fp1", file_name=None, params=None):
    manifest.record(
        collection_name=name,
        file_name=file_name or f"{name}.blend",
        kind="prototype",
        cache_key=name.split("_")[-1],
        fingerprint=fingerprint,
        params=params or {"length": 0.18},
        created_at="2026-06-24T14:00:00",
    )


def test_record_and_get(tmp_path):
    m = CacheManifest(tmp_path)
    _record(m, "Proto_abc")
    entry = m.get("Proto_abc")
    assert entry is not None
    assert entry["file"] == "Proto_abc.blend"
    assert entry["source_fingerprint"] == "fp1"
    assert entry["params"] == {"length": 0.18}


def test_get_missing_returns_none(tmp_path):
    m = CacheManifest(tmp_path)
    assert m.get("nope") is None


def test_record_persists_across_instances(tmp_path):
    m1 = CacheManifest(tmp_path)
    _record(m1, "Proto_abc")
    # A fresh manifest over the same dir must see the persisted entry.
    m2 = CacheManifest(tmp_path)
    assert m2.get("Proto_abc") is not None


def test_save_writes_valid_json_with_schema(tmp_path):
    m = CacheManifest(tmp_path)
    _record(m, "Proto_abc")
    data = json.loads((tmp_path / CacheManifest.FILENAME).read_text(encoding="utf-8"))
    assert data["schema"] == CacheManifest.SCHEMA
    assert len(data["entries"]) == 1


def test_is_valid_matches_fingerprint(tmp_path):
    m = CacheManifest(tmp_path)
    _record(m, "Proto_abc", fingerprint="fp1")
    assert m.is_valid("Proto_abc", "fp1") is True
    assert m.is_valid("Proto_abc", "fp2") is False
    assert m.is_valid("missing", "fp1") is False


def test_prune_stale_removes_mismatched_entry_and_file(tmp_path):
    m = CacheManifest(tmp_path)
    stale_blend = tmp_path / "Proto_old.blend"
    stale_blend.write_bytes(b"old")
    _record(m, "Proto_old", fingerprint="OLD", file_name="Proto_old.blend")

    removed = m.prune_stale("NEW")

    assert removed == ["Proto_old"]
    assert m.get("Proto_old") is None
    assert not stale_blend.exists()


def test_prune_stale_keeps_matching_entry(tmp_path):
    m = CacheManifest(tmp_path)
    keep_blend = tmp_path / "Proto_keep.blend"
    keep_blend.write_bytes(b"keep")
    _record(m, "Proto_keep", fingerprint="NEW", file_name="Proto_keep.blend")

    removed = m.prune_stale("NEW")

    assert removed == []
    assert m.get("Proto_keep") is not None
    assert keep_blend.exists()


def test_prune_stale_persists_removal(tmp_path):
    m = CacheManifest(tmp_path)
    (tmp_path / "Proto_old.blend").write_bytes(b"old")
    _record(m, "Proto_old", fingerprint="OLD")
    m.prune_stale("NEW")
    # Reload from disk: the removal must have been saved.
    assert CacheManifest(tmp_path).get("Proto_old") is None


def test_orphans_detects_untracked_blend(tmp_path):
    m = CacheManifest(tmp_path)
    _record(m, "Proto_tracked", file_name="Proto_tracked.blend")
    (tmp_path / "Proto_tracked.blend").write_bytes(b"x")
    (tmp_path / "Proto_orphan.blend").write_bytes(b"y")

    assert m.orphans() == ["Proto_orphan.blend"]


def test_corrupt_manifest_starts_fresh(tmp_path):
    (tmp_path / CacheManifest.FILENAME).write_text("{ not valid json", encoding="utf-8")
    m = CacheManifest(tmp_path)
    assert m.entries() == []


def test_schema_mismatch_starts_fresh(tmp_path):
    (tmp_path / CacheManifest.FILENAME).write_text(
        json.dumps({"schema": 999, "entries": [{"collection_name": "x"}]}),
        encoding="utf-8",
    )
    m = CacheManifest(tmp_path)
    assert m.entries() == []


def test_no_manifest_file_means_empty(tmp_path):
    m = CacheManifest(tmp_path)
    assert m.entries() == []


def test_drop_missing_files_removes_entry_without_file(tmp_path):
    m = CacheManifest(tmp_path)
    # Two recorded entries; only one has its .blend on disk.
    (tmp_path / "Proto_present.blend").write_bytes(b"x")
    _record(m, "Proto_present", file_name="Proto_present.blend")
    _record(m, "Proto_gone", file_name="Proto_gone.blend")  # no file written

    removed = m.drop_missing_files()

    assert removed == ["Proto_gone"]
    assert m.get("Proto_present") is not None
    assert m.get("Proto_gone") is None


def test_drop_missing_files_persists(tmp_path):
    m = CacheManifest(tmp_path)
    _record(m, "Proto_gone", file_name="Proto_gone.blend")
    m.drop_missing_files()
    assert CacheManifest(tmp_path).get("Proto_gone") is None


def test_prune_stale_skips_malformed_file_without_touching_dir(tmp_path):
    # A stale entry whose 'file' is empty must be dropped, but must NOT cause an
    # unlink of the cache dir itself or any unrelated path.
    m = CacheManifest(tmp_path)
    m.record(
        collection_name="Broken",
        file_name="",  # malformed
        kind="prototype",
        cache_key="k",
        fingerprint="OLD",
        params={},
        created_at="t",
    )
    bystander = tmp_path / "keep.blend"
    bystander.write_bytes(b"keep")

    removed = m.prune_stale("NEW")

    assert removed == ["Broken"]
    assert tmp_path.exists()  # dir untouched
    assert bystander.exists()  # unrelated file untouched


def test_prune_stale_ignores_file_not_matching_collection_name(tmp_path):
    # An entry whose 'file' points at a DIFFERENT collection's blend must not
    # delete that other file.
    m = CacheManifest(tmp_path)
    victim = tmp_path / "SomeoneElse.blend"
    victim.write_bytes(b"data")
    m.record(
        collection_name="Broken",
        file_name="SomeoneElse.blend",  # mismatched: != Broken.blend
        kind="prototype",
        cache_key="k",
        fingerprint="OLD",
        params={},
        created_at="t",
    )

    m.prune_stale("NEW")

    assert victim.exists()  # untouched despite the stale entry being dropped
    assert m.get("Broken") is None
