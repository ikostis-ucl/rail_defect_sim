from unittest.mock import MagicMock
from app.geometry.defects.selector import DefectSelector
from app.geometry.defects.sleepers import SkewedSleeperDefect
from app.geometry.defects.fasteners import MissingFastenerPairDefect


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
    from app.geometry.defects.registry import ALL_DEFECTS
    sel = DefectSelector.default()
    expected_count = sum(len(d.variants()) for d in ALL_DEFECTS)
    assert len(sel.all_variants()) == expected_count


def test_register_span_queues_followers_automatically():
    from app.geometry.defects.variant import DefectVariant
    sel = DefectSelector(seed=0)
    v0 = DefectVariant("d", {"position": 0}, MagicMock())
    v1 = DefectVariant("d", {"position": 1}, MagicMock())
    v2 = DefectVariant("d", {"position": 2}, MagicMock())
    sel.register_span([v0, v1, v2])

    # Force defect to trigger by mocking rng
    sel._rng.random = lambda: 0.0   # always below DEFECT_PROBABILITY
    sel._rng.choice = lambda seq: seq[0]

    result0 = sel.select_variant()
    result1 = sel.select_variant()  # follower — no re-roll
    result2 = sel.select_variant()  # follower — no re-roll
    assert result0 is v0
    assert result1 is v1
    assert result2 is v2


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


def test_defect_probability_reflects_span_coverage():
    # 10% of sections *start* a defect. Displacement spans cover 5-7 consecutive
    # sections, so the effective defective-section rate is higher than 10%.
    # With the current defect mix the expected rate is roughly 25-35%.
    sel = DefectSelector.default(seed=7)
    n = 2000
    defective = sum(1 for _ in range(n) if sel.select_variant() is not None)
    ratio = defective / n
    assert 0.15 < ratio < 0.50  # span followers raise effective coverage above 10%


def test_forced_selector_always_returns_a_variant():
    from app.geometry.defects.rails.rail_displacement import RightRailLateralDisplacementDefect
    sel = DefectSelector.forced("right_rail_lateral_displacement", seed=0)
    for _ in range(50):
        v = sel.select_variant()
        assert v is not None
        assert v.defect_name == RightRailLateralDisplacementDefect.NAME


def test_forced_selector_unknown_name_raises():
    import pytest
    with pytest.raises(ValueError, match="Unknown defect"):
        DefectSelector.forced("nonexistent_defect")


def test_forced_selector_only_contains_named_defect():
    from app.geometry.defects.rails.rail_displacement import RightRailLateralDisplacementDefect
    sel = DefectSelector.forced("right_rail_lateral_displacement")
    for v in sel.all_variants():
        assert v.defect_name == RightRailLateralDisplacementDefect.NAME


def test_custom_seed_different_from_no_seed():
    # Two selectors with different seeds should differ eventually
    sel1 = DefectSelector.default(seed=1)
    sel2 = DefectSelector.default(seed=99999)
    results1 = [sel1.select_variant() for _ in range(100)]
    results2 = [sel2.select_variant() for _ in range(100)]
    ids1 = [v.identifier if v else None for v in results1]
    ids2 = [v.identifier if v else None for v in results2]
    assert ids1 != ids2
