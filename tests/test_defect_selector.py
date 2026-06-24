from unittest.mock import MagicMock
from app.geometry.defects.selector import DefectSelector
from app.geometry.defects.skewed_sleeper import SkewedSleeperDefect
from app.geometry.defects.missing_fastener import MissingFastenerPairDefect


def _dummy_variant(name="defect"):
    from app.geometry.defects.variant import DefectVariant
    return DefectVariant(name, {}, MagicMock())


def test_empty_selector_returns_none():
    sel = DefectSelector()
    assert sel.select_variant() is None


def test_register_adds_variant():
    sel = DefectSelector()
    v = _dummy_variant()
    sel.register(v)
    assert v in sel.all_variants()


def test_all_variants_returns_copy():
    sel = DefectSelector()
    v = _dummy_variant()
    sel.register(v)
    result = sel.all_variants()
    result.clear()
    assert len(sel.all_variants()) == 1  # original untouched


def test_default_contains_all_registered_defect_variants():
    sel = DefectSelector.default()
    expected_count = (
        len(SkewedSleeperDefect.variants()) + len(MissingFastenerPairDefect.variants())
    )
    assert len(sel.all_variants()) == expected_count


def test_seeded_selector_is_deterministic():
    sel1 = DefectSelector.default(seed=42)
    sel2 = DefectSelector.default(seed=42)
    results1 = [sel1.select_variant() for _ in range(50)]
    results2 = [sel2.select_variant() for _ in range(50)]
    ids1 = [v.identifier if v else None for v in results1]
    ids2 = [v.identifier if v else None for v in results2]
    assert ids1 == ids2


def test_select_variant_returns_registered_variants_only():
    sel = DefectSelector.default(seed=0)
    known_ids = {v.identifier for v in sel.all_variants()}
    for _ in range(200):
        v = sel.select_variant()
        if v is not None:
            assert v.identifier in known_ids


def test_defect_probability_is_roughly_ten_percent():
    sel = DefectSelector.default(seed=7)
    n = 2000
    defective = sum(1 for _ in range(n) if sel.select_variant() is not None)
    ratio = defective / n
    assert 0.05 < ratio < 0.20  # allow generous tolerance


def test_custom_seed_different_from_no_seed():
    # Two selectors with different seeds should differ eventually
    sel1 = DefectSelector.default(seed=1)
    sel2 = DefectSelector.default(seed=99999)
    results1 = [sel1.select_variant() for _ in range(100)]
    results2 = [sel2.select_variant() for _ in range(100)]
    ids1 = [v.identifier if v else None for v in results1]
    ids2 = [v.identifier if v else None for v in results2]
    assert ids1 != ids2
