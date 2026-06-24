"""
Tests for TrackSection pure-Python logic (layout maths, payload, material dispatch).
No bpy calls are exercised here — the Blender stub satisfies the import.
"""
import math
import pytest
from unittest.mock import MagicMock
from app.config.geometry import TrackGeometryConfig
from app.geometry.track_section import TrackSection


def _cfg(**kw) -> TrackGeometryConfig:
    return TrackGeometryConfig(**kw)


def _section(**kw) -> TrackSection:
    return TrackSection(config=_cfg(**kw))


# ── construction ──────────────────────────────────────────────────────────────

def test_default_construction_uses_default_config():
    s = TrackSection()
    assert s.config == TrackGeometryConfig()


def test_config_stored_on_instance():
    cfg = TrackGeometryConfig(rail_spacing=1.6)
    s = TrackSection(config=cfg)
    assert s.config is cfg


# ── _compute_layout ───────────────────────────────────────────────────────────

def test_layout_rails_are_symmetric_around_center():
    ts = _section(rail_spacing=1.4)
    layout = ts._compute_layout(0.0)
    assert layout.left_rail_x == pytest.approx(-0.7)
    assert layout.right_rail_x == pytest.approx(0.7)


def test_layout_rails_shift_with_center_x():
    ts = _section(rail_spacing=1.4)
    layout = ts._compute_layout(2.0)
    assert layout.left_rail_x == pytest.approx(2.0 - 0.7)
    assert layout.right_rail_x == pytest.approx(2.0 + 0.7)


def test_layout_sleepers_outside_rails():
    ts = _section()
    layout = ts._compute_layout(0.0)
    assert layout.left_sleeper_x < layout.left_rail_x
    assert layout.right_sleeper_x > layout.right_rail_x


def test_layout_middle_sleeper_between_rails():
    ts = _section()
    layout = ts._compute_layout(0.0)
    assert layout.left_rail_x < layout.middle_sleeper_x < layout.right_rail_x


def test_layout_widths_are_positive():
    ts = _section()
    layout = ts._compute_layout(0.0)
    assert layout.side_sleeper_width > 0
    assert layout.middle_sleeper_width > 0


def test_layout_wider_rail_spacing_gives_wider_middle():
    narrow = _section(rail_spacing=1.0)
    wide = _section(rail_spacing=2.0)
    assert wide._compute_layout(0.0).middle_sleeper_width > narrow._compute_layout(0.0).middle_sleeper_width


# ── geometry_payload ──────────────────────────────────────────────────────────

def test_geometry_payload_contains_config_fields():
    import dataclasses
    ts = TrackSection()
    payload = ts.geometry_payload()
    for f in dataclasses.fields(TrackGeometryConfig):
        assert f.name in payload


def test_geometry_payload_no_derived_section_pitch():
    payload = TrackSection().geometry_payload()
    assert "section_pitch" not in payload


def test_geometry_payload_values_match_config():
    cfg = TrackGeometryConfig(rail_spacing=1.6, sleeper_height=0.15)
    ts = TrackSection(config=cfg)
    p = ts.geometry_payload()
    assert p["rail_spacing"] == pytest.approx(1.6)
    assert p["sleeper_height"] == pytest.approx(0.15)


def test_geometry_payload_no_ballast_keys():
    for key in TrackSection().geometry_payload():
        assert "ballast" not in key


# ── z helpers ─────────────────────────────────────────────────────────────────

def test_sleeper_center_z():
    ts = _section(sleeper_height=0.12)
    assert ts._sleeper_center_z(0.0) == pytest.approx(0.06)


def test_sleeper_top_z():
    ts = _section(sleeper_height=0.12)
    assert ts._sleeper_top_z(0.0) == pytest.approx(0.12)


def test_rail_center_z_above_sleeper_top():
    ts = _section(sleeper_height=0.12, rail_height=0.16)
    assert ts._rail_center_z(0.0) > ts._sleeper_top_z(0.0)


# ── role constants ────────────────────────────────────────────────────────────

def test_sleeper_role_constant():
    assert TrackSection.SLEEPER_ROLE == "sleeper"
    assert "ballast" not in TrackSection.SLEEPER_ROLE


def test_all_role_constants_are_strings():
    for attr in ("SECTION_PARENT_ROLE", "LEFT_RAIL_ROLE", "RIGHT_RAIL_ROLE",
                 "SLEEPER_ROLE", "FASTENER_ROLE"):
        assert isinstance(getattr(TrackSection, attr), str)


# ── apply_materials_to_collection ─────────────────────────────────────────────

def test_apply_materials_dispatches_by_role():
    rail_mat = MagicMock(name="rail_mat")
    sleeper_mat = MagicMock(name="sleeper_mat")
    fastener_mat = MagicMock(name="fastener_mat")

    def _obj(role):
        o = MagicMock()
        o.get.side_effect = lambda key, default=None: role if key == "track_section_role" else default
        o.data = MagicMock()
        o.data.materials = MagicMock()
        return o

    rail_obj     = _obj(TrackSection.LEFT_RAIL_ROLE)
    sleeper_obj  = _obj(TrackSection.SLEEPER_ROLE)
    fastener_obj = _obj(TrackSection.FASTENER_ROLE)
    parent_obj   = _obj(TrackSection.SECTION_PARENT_ROLE)

    collection = MagicMock()
    collection.objects = [rail_obj, sleeper_obj, fastener_obj, parent_obj]

    TrackSection.apply_materials_to_collection(
        collection,
        rail_material=rail_mat,
        sleeper_material=sleeper_mat,
        fastener_material=fastener_mat,
    )

    rail_obj.data.materials.append.assert_called_with(rail_mat)
    sleeper_obj.data.materials.append.assert_called_with(sleeper_mat)
    fastener_obj.data.materials.append.assert_called_with(fastener_mat)
    parent_obj.data.materials.append.assert_not_called()
