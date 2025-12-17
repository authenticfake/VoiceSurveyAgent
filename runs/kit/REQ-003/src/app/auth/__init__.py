"""
Auth package.

IMPORTANT:
Keep this module import-light to avoid circular imports during test collection.
We also extend __path__ so the package can span multiple REQ-* folders on PYTHONPATH.
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
