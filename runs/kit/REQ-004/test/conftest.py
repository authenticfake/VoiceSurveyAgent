"""
Pytest configuration and fixtures for REQ-004 tests.
"""

import pytest
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest_asyncio


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Configure anyio backend for async tests."""
    return "asyncio"


@pytest_asyncio.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session