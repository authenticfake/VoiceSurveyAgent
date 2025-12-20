"""
Contacts package.

Keep import side-effect free: do not import repositories at import time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.contacts.repository import ContactRepository  # noqa: F401
