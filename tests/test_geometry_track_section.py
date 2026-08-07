"""
Tests for TrackSection pure-Python logic (layout maths, payload, material dispatch).
No bpy calls are exercised here — the Blender stub satisfies the import.
"""
import math
import pytest
from unittest.mock import MagicMock
from app.config.geometry import RailConfig, TrackGeometryConfig
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


def test_layout_sleeper_spans_beyond_rails():
    ts = _section()
    layout = ts._compute_layout(0.0)
    sleeper_left  = layout.sleeper_x - layout.sleeper_width / 2
    sleeper_right = layout.sleeper_x + layout.sleeper_width / 2
    assert sleeper_left  < layout.left_rail_x
    assert sleeper_right > layout.right_rail_x


def test_layout_sleeper_centered_on_symmetric_track():
    ts = _section(rail_spacing=1.4)
    layout = ts._compute_layout(0.0)
    assert layout.sleeper_x == pytest.approx(0.0)


def test_layout_sleeper_width_positive():
    ts = _section()
    layout = ts._compute_layout(0.0)
    assert layout.sleeper_width > 0


def test_layout_wider_rail_spacing_gives_wider_sleeper():
    narrow = _section(rail_spacing=1.0)
    wide   = _section(rail_spacing=2.0)
    assert wide._compute_layout(0.0).sleeper_width > narrow._compute_layout(0.0).sleeper_width


def test_layout_wider_rail_foot_gives_wider_sleeper():
    cfg_narrow = TrackGeometryConfig(right_rail=RailConfig(foot_width=0.140))
    cfg_wide   = TrackGeometryConfig(right_rail=RailConfig(foot_width=0.180))
    narrow_layout = TrackSection(config=cfg_narrow)._compute_layout(0.0)
    wide_layout   = TrackSection(config=cfg_wide)._compute_layout(0.0)
    assert wide_layout.sleeper_width > narrow_layout.sleeper_width


# ── geometry_payload ──────────────────────────────────────────────────────────

def test_geometry_payload_contains_config_fields():
    import dataclasses
    ts = TrackSection()
    payload = ts.geometry_payload()
    for f in dataclasses.fields(TrackGeometryConfig):
        assert f.name in payload


def test_geometry_payload_includes_section_pitch():
    payload = TrackSection().geometry_payload()
    assert "section_pitch" in payload


def test_geometry_payload_values_match_config():
    cfg = TrackGeometryConfig(rail_spacing=1.6, sleeper_height=0.15)
    ts = TrackSection(config=cfg)
    p = ts.geometry_payload()
    assert p["rail_spacing"] == pytest.approx(1.6)
    assert p["sleeper_height"] == pytest.approx(0.15)


def test_geometry_payload_rail_configs_are_nested_dicts():
    payload = TrackSection().geometry_payload()
    assert isinstance(payload["left_rail"], dict)
    assert isinstance(payload["right_rail"], dict)
    assert "pad_thickness" in payload["left_rail"]
    assert "pad_thickness" in payload["right_rail"]


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
    rail_cfg = RailConfig(height=0.16)
    ts = _section(sleeper_height=0.12)
    assert ts._rail_center_z(0.0, rail_cfg) > ts._sleeper_top_z(0.0)


# ── contiguity ────────────────────────────────────────────────────────────────

def test_rail_foot_bottom_equals_sleeper_top_plus_pad():
    """Rail foot must rest exactly on the pad; no gap or overlap with sleeper."""
    pad = 0.007
    height = 0.159
    rail_cfg = RailConfig(pad_thickness=pad, height=height)
    ts = _section(sleeper_height=0.200)
    sleeper_top = ts._sleeper_top_z(0.0)
    rail_center = ts._rail_center_z(0.0, rail_cfg)
    rail_foot_bottom = rail_center - height / 2
    assert rail_foot_bottom == pytest.approx(sleeper_top + pad)


def test_fastener_depth_is_the_standard_clip_length():
    """The clip length exceeds the pad, so it is used unchanged."""
    ts = TrackSection()
    cfg = ts.config
    assert ts._fastener_depth(cfg.left_rail) == pytest.approx(cfg.screw_length)


def test_rail_no_overlap_with_sleeper():
    """Rail foot bottom must not be below the sleeper top surface."""
    ts = TrackSection()
    sleeper_top = ts._sleeper_top_z(0.0)
    for rail_cfg in (ts.config.left_rail, ts.config.right_rail):
        rail_center = ts._rail_center_z(0.0, rail_cfg)
        rail_foot_bottom = rail_center - rail_cfg.height / 2
        assert rail_foot_bottom >= sleeper_top, (
            f"Rail overlaps sleeper: foot_bottom={rail_foot_bottom:.4f} "
            f"< sleeper_top={sleeper_top:.4f}"
        )


# ── role constants ────────────────────────────────────────────────────────────

def test_sleeper_role_constant():
    assert TrackSection.SLEEPER_ROLE == "sleeper"
    assert "ballast" not in TrackSection.SLEEPER_ROLE


def test_left_right_rail_roles_distinct():
    assert TrackSection.LEFT_RAIL_ROLE != TrackSection.RIGHT_RAIL_ROLE


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

    left_rail_obj  = _obj(TrackSection.LEFT_RAIL_ROLE)
    right_rail_obj = _obj(TrackSection.RIGHT_RAIL_ROLE)
    sleeper_obj    = _obj(TrackSection.SLEEPER_ROLE)
    fastener_obj   = _obj(TrackSection.FASTENER_ROLE)
    parent_obj     = _obj(TrackSection.SECTION_PARENT_ROLE)

    collection = MagicMock()
    collection.objects = [left_rail_obj, right_rail_obj, sleeper_obj, fastener_obj, parent_obj]

    TrackSection.apply_materials_to_collection(
        collection,
        rail_material=rail_mat,
        sleeper_material=sleeper_mat,
        fastener_material=fastener_mat,
    )

    left_rail_obj.data.materials.append.assert_called_with(rail_mat)
    right_rail_obj.data.materials.append.assert_called_with(rail_mat)
    sleeper_obj.data.materials.append.assert_called_with(sleeper_mat)
    fastener_obj.data.materials.append.assert_called_with(fastener_mat)
    parent_obj.data.materials.append.assert_not_called()


def test_rails_are_configurable_independently():
    """A defect often appears on one rail only, so the two must differ freely."""
    cfg = TrackGeometryConfig(
        left_rail=RailConfig(head_width=0.070, height=0.159),
        right_rail=RailConfig(head_width=0.074, height=0.172),
    )
    ts = TrackSection(config=cfg)
    assert ts.config.left_rail.head_width != ts.config.right_rail.head_width
    assert ts.config.left_rail.height != ts.config.right_rail.height


def test_rail_config_has_no_defect_fields():
    """lift/angle are gone: defects deform the mesh, they are not config."""
    import dataclasses
    names = {f.name for f in dataclasses.fields(RailConfig)}
    assert "lift" not in names
    assert "angle" not in names
