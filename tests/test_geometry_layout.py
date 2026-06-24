import pytest
from app.geometry.layout import TrackSectionLayout


def _make(**overrides):
    defaults = dict(
        left_sleeper_x=-0.8,
        left_rail_x=-0.7,
        middle_sleeper_x=0.0,
        middle_sleeper_width=1.28,
        right_rail_x=0.7,
        right_sleeper_x=0.8,
        side_sleeper_width=0.192,
    )
    defaults.update(overrides)
    return TrackSectionLayout(**defaults)


def test_fields_accessible():
    layout = _make()
    assert layout.left_sleeper_x == pytest.approx(-0.8)
    assert layout.left_rail_x == pytest.approx(-0.7)
    assert layout.middle_sleeper_x == pytest.approx(0.0)
    assert layout.middle_sleeper_width == pytest.approx(1.28)
    assert layout.right_rail_x == pytest.approx(0.7)
    assert layout.right_sleeper_x == pytest.approx(0.8)
    assert layout.side_sleeper_width == pytest.approx(0.192)


def test_frozen_rejects_mutation():
    layout = _make()
    with pytest.raises(Exception):
        layout.left_sleeper_x = 0.0  # type: ignore[misc]


def test_equality():
    a = _make()
    b = _make()
    assert a == b


def test_inequality_on_different_value():
    a = _make(left_sleeper_x=-0.8)
    b = _make(left_sleeper_x=-0.9)
    assert a != b
