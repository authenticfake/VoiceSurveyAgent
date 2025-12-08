"""
Pytest configuration and fixtures for campaign tests.
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.schemas import UserRole
from app.campaigns.models import Campaign, CampaignStatusEnum, User
from app.config import get_settings
from app.main import app
from app.shared.database import Base, get_db_session

settings = get_settings()

# Test database URL - use a separate test database
TEST_DATABASE_URL = str(settings.database_url).replace(
    "postgresql://", "postgresql+asyncpg://"
)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with transaction rollback."""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        # Start a transaction
        async with session.begin():
            yield session
            # Rollback after test
            await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database session override."""

    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()

def create_test_token(
    sub: str = "test-user-sub",
    email: str = "test@example.com",
    name: str = "Test User",
    role: str = "campaign_manager",
    expires_delta: timedelta | None = None,
) -> str:
    """Create a test JWT token."""
    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "name": name,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.oidc_issuer_url,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, "test-secret", algorithm="HS256")

@pytest.fixture
def admin_token() -> str:
    """Create admin user token."""
    return create_test_token(
        sub="admin-sub",
        email="admin@example.com",
        name="Admin User",
        role="admin",
    )

@pytest.fixture
def campaign_manager_token() -> str:
    """Create campaign manager token."""
    return create_test_token(
        sub="manager-sub",
        email="manager@example.com",
        name="Campaign Manager",
        role="campaign_manager",
    )

@pytest.fixture
def viewer_token() -> str:
    """Create viewer token."""
    return create_test_token(
        sub="viewer-sub",
        email="viewer@example.com",
        name="Viewer User",
        role="viewer",
    )

@pytest.fixture
def expired_token() -> str:
    """Create expired token."""
    return create_test_token(expires_delta=timedelta(hours=-1))

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(
        id=uuid4(),
        oidc_sub="manager-sub",
        email="manager@example.com",
        name="Campaign Manager",
        role="campaign_manager",
    )
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def test_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    """Create a test campaign in the database."""
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        description="A test campaign",
        status=CampaignStatusEnum.DRAFT,
        language="en",
        intro_script="Hello, this is a test survey...",
        question_1_text="What is your favorite color?",
        question_1_type="free_text",
        question_2_text="Rate your experience from 1-10",
        question_2_type="scale",
        question_3_text="How many times have you used our service?",
        question_3_type="numeric",
        max_attempts=3,
        retry_interval_minutes=60,
        created_by_user_id=test_user.id,
    )
    db_session.add(campaign)
    await db_session.flush()
    return campaign

@pytest.fixture
def valid_campaign_data() -> dict[str, Any]:
    """Valid campaign creation data."""
    return {
        "name": "New Test Campaign",
        "description": "A new test campaign",
        "language": "en",
        "intro_script": "Hello, this is a survey about customer satisfaction...",
        "question_1": {
            "text": "How satisfied are you with our service?",
            "type": "scale",
        },
        "question_2": {
            "text": "What could we improve?",
            "type": "free_text",
        },
        "question_3": {
            "text": "How many times have you contacted support?",
            "type": "numeric",
        },
        "max_attempts": 3,
        "retry_interval_minutes": 60,
        "allowed_call_start_local": "09:00:00",
        "allowed_call_end_local": "20:00:00",
    }