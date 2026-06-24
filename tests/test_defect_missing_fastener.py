import sys
from unittest.mock import MagicMock
import pytest
from app.geometry.defects.missing_fastener import MissingFastenerPairDefect


def _section_with_fasteners(n=8):
    section = MagicMock()
    section.fasteners = [MagicMock(name=f"f{i}") for i in range(n)]
    return section


def test_name():
    assert MissingFastenerPairDefect.NAME == "missing_fastener_pair"


def test_variants_count():
    assert len(MissingFastenerPairDefect.variants()) == 4


def test_variant_names_match_class_name():
    for v in MissingFastenerPairDefect.variants():
        assert v.defect_name == MissingFastenerPairDefect.NAME


def test_variant_params_contain_pair_index():
    for v in MissingFastenerPairDefect.variants():
        assert "pair_index" in v.defect_params


def test_variant_pair_indices():
    indices = [v.defect_params["pair_index"] for v in MissingFastenerPairDefect.variants()]
    assert sorted(indices) == [0, 1, 2, 3]


def test_variant_defect_class_is_missing_fastener():
    for v in MissingFastenerPairDefect.variants():
        assert v.defect_class is MissingFastenerPairDefect


def test_apply_removes_two_fasteners():
    section = _section_with_fasteners(8)
    original_count = len(section.fasteners)
    MissingFastenerPairDefect.apply(section, {"pair_index": 0})
    assert len(section.fasteners) == original_count - 2


def test_apply_pair_0_removes_indices_0_and_1():
    section = _section_with_fasteners(8)
    kept = section.fasteners[2:]
    MissingFastenerPairDefect.apply(section, {"pair_index": 0})
    assert section.fasteners == kept


def test_apply_pair_1_removes_indices_2_and_3():
    section = _section_with_fasteners(8)
    expected = section.fasteners[:2] + section.fasteners[4:]
    MissingFastenerPairDefect.apply(section, {"pair_index": 1})
    assert section.fasteners == expected


def test_apply_pair_3_removes_last_two():
    section = _section_with_fasteners(8)
    expected = section.fasteners[:6]
    MissingFastenerPairDefect.apply(section, {"pair_index": 3})
    assert section.fasteners == expected


def test_apply_out_of_range_pair_is_noop():
    section = _section_with_fasteners(4)
    original_count = len(section.fasteners)
    # pair_index=3 → start_idx=6,7 which are >= 4, so nothing removed
    MissingFastenerPairDefect.apply(section, {"pair_index": 3})
    assert len(section.fasteners) == original_count


def test_apply_calls_bpy_remove():
    import bpy
    section = _section_with_fasteners(8)
    bpy.data.objects.remove.reset_mock()
    MissingFastenerPairDefect.apply(section, {"pair_index": 0})
    assert bpy.data.objects.remove.call_count == 2
