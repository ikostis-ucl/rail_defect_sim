"""Geometry builders.

``TrackBuilder`` and ``TrackSection`` import ``bpy``, so they are exposed
lazily (PEP 562). Importing ``app.geometry.defects`` or any other submodule
therefore does not drag Blender in, which is what lets defect metadata be read
outside Blender — by the validation layer and by tooling.

``from app.geometry import TrackBuilder`` still works exactly as before; the
import of ``bpy`` is simply deferred to that moment.
"""

__all__ = ["TrackBuilder", "TrackSection"]

_LAZY = {
    "TrackBuilder": "app.geometry.track_builder",
    "TrackSection": "app.geometry.track_section",
}


def __getattr__(name: str):
    module_path = _LAZY.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module_path), name)


def __dir__():
    return sorted(__all__)
