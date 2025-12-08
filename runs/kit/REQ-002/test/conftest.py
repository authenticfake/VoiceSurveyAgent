"""
Pytest configuration and fixtures.

Shared fixtures for authentication tests.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    from app.auth import middleware
    middleware._auth_middleware._auth_service = None
    yield


@pytest.fixture
def anyio_backend():
    """Configure anyio backend for async tests."""
    return "asyncio"