"""
Pytest configuration and fixtures for REQ-008 tests.

REQ-008: Call scheduler service
"""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sys
from pathlib import Path

# Add this kit's src/ to sys.path so `import app.*` works when running tests directly
KIT_ROOT = Path(__file__).resolve().parents[1]
SRC = KIT_ROOT / "src"
sys.path.insert(0, str(SRC))



# Set test environment
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://afranco:Andrea.1@localhost:5432/voicesurveyagent")
os.environ.setdefault("OIDC_ISSUER_URL", "http://localhost:8880")
os.environ.setdefault("OIDC_CLIENT_ID", "voice-survey-agent")
os.environ.setdefault("OIDC_CLIENT_SECRET", "wQGovP2T32xHHGVwEzRO7M2WLcSBuBPl")
os.environ.setdefault("JWT_SECRET_KEY", "your-secure-secret-key-min-32-chars")


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for testing.

    Uses a real database connection if DATABASE_URL is set,
    otherwise skips tests requiring database.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set, skipping database tests")

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()