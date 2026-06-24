"""
Tests for SectionCacheBase._make_cache_key (pure SHA-256 logic, no bpy calls).
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.geometry.cache.base import SectionCacheBase


def _key(payload: dict) -> str:
    return SectionCacheBase._make_cache_key(payload)


def test_key_is_16_hex_chars():
    k = _key({"a": 1})
    assert len(k) == 16
    assert all(c in "0123456789abcdef" for c in k)


def test_key_is_deterministic():
    assert _key({"x": 1.0}) == _key({"x": 1.0})


def test_key_changes_with_value():
    assert _key({"x": 1.0}) != _key({"x": 2.0})


def test_key_changes_with_key_name():
    assert _key({"a": 1}) != _key({"b": 1})


def test_key_is_order_independent():
    # sort_keys=True means {"a":1,"b":2} == {"b":2,"a":1}
    assert _key({"a": 1, "b": 2}) == _key({"b": 2, "a": 1})


def test_key_distinguishes_float_and_string():
    # JSON serialisation preserves types — float 1.0 and string "1.0" must differ.
    k_float = _key({"v": 1.0})
    k_str   = _key({"v": "1.0"})
    assert k_float != k_str


def test_key_handles_nested_dicts():
    # Nested dicts (from RailConfig.to_dict()) must be serialised recursively.
    flat = _key({"rail": "x"})
    nested = _key({"rail": {"angle": 0.0}})
    assert flat != nested
    # Same nested structure gives same key
    assert _key({"rail": {"angle": 0.0, "width": 0.06}}) == _key({"rail": {"width": 0.06, "angle": 0.0}})


def test_empty_payload_produces_key():
    k = _key({})
    assert len(k) == 16


def test_distinct_payloads_give_distinct_keys():
    # cache_key is geometry-params-only (no version); any value difference
    # in the payload must change the key.
    assert _key({"sleeper_height": 0.12}) != _key({"sleeper_height": 0.13})


def test_init_creates_cache_dir(tmp_path):
    cache_dir = tmp_path / "test_cache"
    assert not cache_dir.exists()

    SectionCacheBase(cache_dir)
    assert cache_dir.exists()


def test_init_computes_fingerprint_and_manifest(tmp_path):
    cache = SectionCacheBase(tmp_path / "c")
    # No source files -> still a stable 12-char fingerprint, and a manifest.
    assert len(cache.fingerprint) == 12
    assert cache.manifest is not None
