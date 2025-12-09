"""
Pytest configuration and fixtures for REQ-005 tests.
"""

import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio backend for async tests."""
    return "asyncio"