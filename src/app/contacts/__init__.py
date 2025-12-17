"""
Contacts package.

Do not import router/service here to avoid side effects.
"""

from pkgutil import extend_path

# Make app.contacts a composable namespace package across kits
__path__ = extend_path(__path__, __name__)

from app.contacts.models import Contact, ContactState

__all__ = ["Contact", "ContactState"]
