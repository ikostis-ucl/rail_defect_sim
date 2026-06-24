"""Shared Blender object utility functions for the geometry package."""


def move_to_collection(obj, collection) -> None:
    """Relink *obj* to *collection*, removing it from all current collections."""
    if collection is None:
        return
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)


def parent_object(obj, parent) -> None:
    """Parent *obj* to *parent* without keeping transform."""
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()


def replace_material(obj, material) -> None:
    """Replace all materials on *obj* with *material*."""
    if material is None or getattr(obj, "data", None) is None:
        return
    slot = getattr(obj.data, "materials", None)
    if slot is None:
        return
    slot.clear()
    slot.append(material)
