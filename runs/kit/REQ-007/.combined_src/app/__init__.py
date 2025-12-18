"""
Top-level `app` package for kits.

We extend the package path so `app.*` can be composed across multiple kit/src
folders on sys.path (REQ-007 provides app.contacts..., other kits provide app.auth...).
"""

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
