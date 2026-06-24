import json
import pytest
from unittest.mock import MagicMock
from app.geometry.defects.variant import DefectVariant


def _variant(name="skewed_sleeper", params=None, cls=None):
    if params is None:
        params = {"angle_deg": 2.0}
    if cls is None:
        cls = MagicMock()
    return DefectVariant(name, params, cls)


def test_identifier_format():
    v = _variant(name="skewed_sleeper", params={"angle_deg": 2.0})
    assert v.identifier == 'skewed_sleeper:{"angle_deg": 2.0}'


def test_identifier_keys_are_sorted():
    v = _variant(params={"z": 1, "a": 2})
    payload = json.loads(v.identifier.split(":", 1)[1])
    assert list(payload.keys()) == sorted(payload.keys())


def test_identifier_is_deterministic():
    v1 = _variant()
    v2 = _variant()
    assert v1.identifier == v2.identifier


def test_apply_calls_defect_class_apply():
    defect_cls = MagicMock()
    params = {"angle_deg": -5.0}
    v = DefectVariant("skewed_sleeper", params, defect_cls)
    section = MagicMock()
    v.apply(section)
    defect_cls.apply.assert_called_once_with(section, params)


def test_frozen_rejects_mutation():
    v = _variant()
    with pytest.raises(Exception):
        v.defect_name = "other"  # type: ignore[misc]


def test_defect_class_excluded_from_equality():
    cls_a = MagicMock()
    cls_b = MagicMock()
    v1 = DefectVariant("name", {"k": 1}, cls_a)
    v2 = DefectVariant("name", {"k": 1}, cls_b)
    assert v1 == v2


def test_identifier_acts_as_stable_hash_key():
    # DefectVariant cannot be hashed (contains a dict field), but its
    # .identifier string is stable and serves as a dict key instead.
    cls_a = MagicMock()
    cls_b = MagicMock()
    v1 = DefectVariant("name", {"k": 1}, cls_a)
    v2 = DefectVariant("name", {"k": 1}, cls_b)
    assert v1.identifier == v2.identifier


def test_different_names_not_equal():
    cls = MagicMock()
    v1 = DefectVariant("aaa", {}, cls)
    v2 = DefectVariant("bbb", {}, cls)
    assert v1 != v2


def test_different_params_not_equal():
    cls = MagicMock()
    v1 = DefectVariant("name", {"a": 1}, cls)
    v2 = DefectVariant("name", {"a": 2}, cls)
    assert v1 != v2
