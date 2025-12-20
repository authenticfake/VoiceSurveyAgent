"""
Call management module.

NOTE:
This package __init__ MUST be lightweight.
Do NOT import SQLAlchemy models here, otherwise importing any submodule
(e.g. app.calls.scheduler) triggers ORM mapping at import time.
"""

__all__: list[str] = []
