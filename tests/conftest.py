"""
Install stubs for Blender's modules into sys.modules before any app imports.

``bpy`` and ``mathutils`` only exist inside Blender's Python interpreter, so
tests run with MagicMocks that satisfy import-time attribute access. Individual
tests that need specific behaviour patch the stub directly.

``mathutils`` matters as much as ``bpy``: ``app/camera/camera_animator.py``
imports it, so without a stub the whole camera module is untestable — which is
how a broken settings reference in it once reached a real Blender run.
"""
import sys
import types
from unittest.mock import MagicMock

# Build a bpy stub module
_bpy = MagicMock(name="bpy")

# bpy.app.handlers needs to behave like a module with list attributes
_handlers = MagicMock()
_handlers.render_init = []
_handlers.render_complete = []
_handlers.render_post = []
_handlers.render_cancel = []
_bpy.app.handlers = _handlers

sys.modules.setdefault("bpy", _bpy)

# mathutils ships with Blender; app/camera imports it at module scope.
sys.modules.setdefault("mathutils", MagicMock(name="mathutils"))
