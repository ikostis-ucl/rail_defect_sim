from app.geometry.defects.registry import ALL_DEFECTS
from app.geometry.defects.base import Defect
from app.geometry.defects.sleepers import SkewedSleeperDefect
from app.geometry.defects.fasteners import MissingFastenerPairDefect


def test_all_defects_is_nonempty():
    assert len(ALL_DEFECTS) > 0


def test_all_defects_contains_skewed_sleeper():
    assert SkewedSleeperDefect in ALL_DEFECTS


def test_all_defects_contains_missing_fastener():
    assert MissingFastenerPairDefect in ALL_DEFECTS


def test_all_defects_are_defect_subclasses():
    for defect_cls in ALL_DEFECTS:
        assert issubclass(defect_cls, Defect)


def test_all_defects_have_name():
    for defect_cls in ALL_DEFECTS:
        assert isinstance(defect_cls.NAME, str)
        assert defect_cls.NAME != ""


def test_all_defects_have_unique_names():
    names = [d.NAME for d in ALL_DEFECTS]
    assert len(names) == len(set(names))


def test_all_defects_have_variants():
    for defect_cls in ALL_DEFECTS:
        variants = defect_cls.variants()
        assert len(variants) > 0


def test_no_ballast_names_in_registry():
    for defect_cls in ALL_DEFECTS:
        assert "ballast" not in defect_cls.NAME
