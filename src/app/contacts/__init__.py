from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.contacts.repository import ContactRepository  # noqa: F401

from pkgutil import extend_path

# Make app.contacts a composable namespace package across kits
__path__ = extend_path(__path__, __name__)

from app.contacts.models import Contact, ContactState

__all__ = ["Contact", "ContactState"]
