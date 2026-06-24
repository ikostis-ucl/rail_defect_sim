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


def test_key_treats_float_and_string_consistently():
    # Values are str()-converted before hashing, so float 1.0 → "1.0"
    k_float = _key({"v": 1.0})
    k_str   = _key({"v": "1.0"})
    assert k_float == k_str


def test_empty_payload_produces_key():
    k = _key({})
    assert len(k) == 16


def test_different_version_gives_different_key():
    assert _key({"cache_version": 1}) != _key({"cache_version": 2})


def test_init_creates_cache_dir(tmp_path):
    cache_dir = tmp_path / "test_cache"
    assert not cache_dir.exists()

    class _TestCache(SectionCacheBase):
        CACHE_VERSION = 1

    _TestCache(cache_dir)
    assert cache_dir.exists()
