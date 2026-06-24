from unittest.mock import MagicMock, call
from app.geometry.utils import move_to_collection, parent_object, replace_material


# ── move_to_collection ────────────────────────────────────────────────────────

def test_move_to_collection_unlinks_old_and_links_new():
    old_col = MagicMock()
    new_col = MagicMock()
    obj = MagicMock()
    obj.users_collection = [old_col]

    move_to_collection(obj, new_col)

    old_col.objects.unlink.assert_called_once_with(obj)
    new_col.objects.link.assert_called_once_with(obj)


def test_move_to_collection_unlinks_multiple_old_collections():
    col_a, col_b = MagicMock(), MagicMock()
    new_col = MagicMock()
    obj = MagicMock()
    obj.users_collection = [col_a, col_b]

    move_to_collection(obj, new_col)

    col_a.objects.unlink.assert_called_once_with(obj)
    col_b.objects.unlink.assert_called_once_with(obj)
    new_col.objects.link.assert_called_once_with(obj)


def test_move_to_collection_noop_when_collection_is_none():
    obj = MagicMock()
    obj.users_collection = [MagicMock()]
    # Should not raise
    move_to_collection(obj, None)
    # users_collection objects should not have been unlinked
    obj.users_collection[0].objects.unlink.assert_not_called()


# ── parent_object ─────────────────────────────────────────────────────────────

def test_parent_object_sets_parent():
    obj = MagicMock()
    parent = MagicMock()
    parent_object(obj, parent)
    assert obj.parent is parent


def test_parent_object_sets_matrix_parent_inverse():
    obj = MagicMock()
    parent = MagicMock()
    parent_object(obj, parent)
    # matrix_parent_inverse should be set to parent.matrix_world.inverted()
    assert obj.matrix_parent_inverse == parent.matrix_world.inverted()


# ── replace_material ──────────────────────────────────────────────────────────

def test_replace_material_clears_and_appends():
    obj = MagicMock()
    mat = MagicMock()
    replace_material(obj, mat)
    obj.data.materials.clear.assert_called_once()
    obj.data.materials.append.assert_called_once_with(mat)


def test_replace_material_noop_when_material_is_none():
    obj = MagicMock()
    replace_material(obj, None)
    obj.data.materials.clear.assert_not_called()
    obj.data.materials.append.assert_not_called()


def test_replace_material_noop_when_obj_has_no_data():
    obj = MagicMock(spec=[])  # no attributes
    mat = MagicMock()
    # Should not raise
    replace_material(obj, mat)


def test_replace_material_noop_when_data_materials_is_none():
    obj = MagicMock()
    obj.data.materials = None
    mat = MagicMock()
    # Should not raise
    replace_material(obj, mat)
