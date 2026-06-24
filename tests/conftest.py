"""
Install a bpy stub into sys.modules before any app imports.

bpy is only available inside Blender's Python interpreter, so tests run
with a MagicMock that satisfies import-time attribute access.  Individual
tests that need specific bpy behaviour patch the stub directly.
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
