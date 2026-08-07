"""The actual rules, grouped by what they are about.

One module per domain — ``geometry`` here, with camera, defect observability and
render budget to follow. ``registry.py`` collects them; nothing else should need
to import a rule directly.
"""

from app.validation.constraints.geometry import GEOMETRY_CONSTRAINTS

__all__ = ["GEOMETRY_CONSTRAINTS"]
