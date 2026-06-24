import pytest
from app.geometry.layout import TrackSectionLayout


def _make(**overrides):
    defaults = dict(
        left_rail_x=-0.7,
        right_rail_x=0.7,
        sleeper_x=0.0,
        sleeper_width=1.42,
    )
    defaults.update(overrides)
    return TrackSectionLayout(**defaults)


def test_fields_accessible():
    layout = _make()
    assert layout.left_rail_x == pytest.approx(-0.7)
    assert layout.right_rail_x == pytest.approx(0.7)
    assert layout.sleeper_x == pytest.approx(0.0)
    assert layout.sleeper_width == pytest.approx(1.42)


def test_frozen_rejects_mutation():
    layout = _make()
    with pytest.raises(Exception):
        layout.left_rail_x = 0.0  # type: ignore[misc]


def test_equality():
    a = _make()
    b = _make()
    assert a == b


def test_inequality_on_different_value():
    a = _make(sleeper_x=0.0)
    b = _make(sleeper_x=0.05)
    assert a != b


def test_sleeper_spans_beyond_rails():
    layout = _make()
    assert layout.sleeper_x - layout.sleeper_width / 2 < layout.left_rail_x
    assert layout.sleeper_x + layout.sleeper_width / 2 > layout.right_rail_x
