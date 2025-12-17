"""
Pytest configuration and fixtures for REQ-007 tests.

We force REQ-007/src at the beginning of sys.path so local modules (app.contacts.*)
win over earlier kits. Other kits are appended to satisfy shared imports (app.auth.*).
"""

from __future__ import annotations

import os
import sys

import pytest


def _src_for(req_dir: str) -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", req_dir, "src"))


# REQ-007 must be first.
sys.path.insert(0, _src_for("."))

# Other kits after.
for req in ["REQ-001", "REQ-002", "REQ-003", "REQ-004", "REQ-005", "REQ-006"]:
    sys.path.append(_src_for(os.path.join("..", req)))


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
