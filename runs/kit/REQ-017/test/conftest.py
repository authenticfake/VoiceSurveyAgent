"""
Test fixtures for REQ-017.

REQ-017: Campaign dashboard stats API
"""

import asyncio
from datetime import datetime, time, timedelta, timezone
from typing import AsyncGenerator, Generator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dashboard.models import (
    Base,
    CallAttempt,
    Campaign,
    CampaignLanguage,
    CampaignStatus,
    Contact,
    ContactOutcome,
    ContactState,
    QuestionType,
    SurveyResponse,
    User,
    UserRole,
)
from app.shared.cache import CacheClient


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    # Use SQLite for testing (in-memory)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def mock_cache() -> CacheClient:
    """Create mock cache client."""

    class MockCacheClient(CacheClient):
        def __init__(self):
            self._store = {}

        async def connect(self):
            pass

        async def disconnect(self):
            pass

        async def get(self, key: str):
            return self._store.get(key)

        async def set(self, key: str, value, ttl_seconds: int):
            self._store[key] = value
            return True

        async def delete(self, key: str):
            self._store.pop(key, None)
            return True

    return MockCacheClient()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=uuid4(),
        oidc_sub="oidc|test001",
        email="test@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    """Create test campaign."""
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        description="Test campaign for stats",
        status=CampaignStatus.RUNNING,
        language=CampaignLanguage.EN,
        intro_script="Hello, this is a test survey.",
        question_1_text="How satisfied are you?",
        question_1_type=QuestionType.SCALE,
        question_2_text="What could we improve?",
        question_2_type=QuestionType.FREE_TEXT,
        question_3_text="Would you recommend us?",
        question_3_type=QuestionType.SCALE,
        max_attempts=3,
        retry_interval_minutes=60,
        allowed_call_start_local=time(9, 0),
        allowed_call_end_local=time(18, 0),
        created_by_user_id=test_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(campaign)
    await db_session.commit()
    return campaign


@pytest_asyncio.fixture
async def test_contacts(
    db_session: AsyncSession, test_campaign: Campaign
) -> list[Contact]:
    """Create test contacts with various states."""
    now = datetime.now(timezone.utc)
    contacts = [
        # Completed contacts
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551001",
            state=ContactState.COMPLETED,
            attempts_count=1,
            last_attempt_at=now - timedelta(hours=2),
            last_outcome=ContactOutcome.COMPLETED,
            created_at=now,
            updated_at=now,
        ),
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551002",
            state=ContactState.COMPLETED,
            attempts_count=2,
            last_attempt_at=now - timedelta(hours=1),
            last_outcome=ContactOutcome.COMPLETED,
            created_at=now,
            updated_at=now,
        ),
        # Refused contact
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551003",
            state=ContactState.REFUSED,
            attempts_count=1,
            last_attempt_at=now - timedelta(hours=3),
            last_outcome=ContactOutcome.REFUSED,
            created_at=now,
            updated_at=now,
        ),
        # Not reached contact
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551004",
            state=ContactState.NOT_REACHED,
            attempts_count=3,
            last_attempt_at=now - timedelta(hours=4),
            last_outcome=ContactOutcome.NO_ANSWER,
            created_at=now,
            updated_at=now,
        ),
        # Pending contacts
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551005",
            state=ContactState.PENDING,
            attempts_count=0,
            created_at=now,
            updated_at=now,
        ),
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551006",
            state=ContactState.PENDING,
            attempts_count=0,
            created_at=now,
            updated_at=now,
        ),
        # In progress contact
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551007",
            state=ContactState.IN_PROGRESS,
            attempts_count=1,
            last_attempt_at=now,
            created_at=now,
            updated_at=now,
        ),
        # Excluded contact
        Contact(
            id=uuid4(),
            campaign_id=test_campaign.id,
            phone_number="+14155551008",
            state=ContactState.EXCLUDED,
            do_not_call=True,
            attempts_count=0,
            created_at=now,
            updated_at=now,
        ),
    ]
    for contact in contacts:
        db_session.add(contact)
    await db_session.commit()
    return contacts


@pytest_asyncio.fixture
async def test_call_attempts(
    db_session: AsyncSession, test_campaign: Campaign, test_contacts: list[Contact]
) -> list[CallAttempt]:
    """Create test call attempts."""
    now = datetime.now(timezone.utc)
    attempts = []

    # Completed calls for first two contacts
    for i, contact in enumerate(test_contacts[:2]):
        attempt = CallAttempt(
            id=uuid4(),
            contact_id=contact.id,
            campaign_id=test_campaign.id,
            attempt_number=1,
            call_id=f"call-{uuid4()}",
            provider_call_id=f"provider-{uuid4()}",
            started_at=now - timedelta(hours=i + 1),
            answered_at=now - timedelta(hours=i + 1) + timedelta(seconds=10),
            ended_at=now - timedelta(hours=i + 1) + timedelta(minutes=3),
            outcome=ContactOutcome.COMPLETED,
            provider_raw_status="completed",
        )
        attempts.append(attempt)

    # Refused call
    refused_contact = test_contacts[2]
    attempt = CallAttempt(
        id=uuid4(),
        contact_id=refused_contact.id,
        campaign_id=test_campaign.id,
        attempt_number=1,
        call_id=f"call-{uuid4()}",
        provider_call_id=f"provider-{uuid4()}",
        started_at=now - timedelta(hours=3),
        answered_at=now - timedelta(hours=3) + timedelta(seconds=10),
        ended_at=now - timedelta(hours=3) + timedelta(seconds=30),
        outcome=ContactOutcome.REFUSED,
        provider_raw_status="completed",
    )
    attempts.append(attempt)

    # No answer calls for not_reached contact
    not_reached_contact = test_contacts[3]
    for i in range(3):
        attempt = CallAttempt(
            id=uuid4(),
            contact_id=not_reached_contact.id,
            campaign_id=test_campaign.id,
            attempt_number=i + 1,
            call_id=f"call-{uuid4()}",
            provider_call_id=f"provider-{uuid4()}",
            started_at=now - timedelta(hours=4 + i),
            ended_at=now - timedelta(hours=4 + i) + timedelta(seconds=30),
            outcome=ContactOutcome.NO_ANSWER,
            provider_raw_status="no-answer",
        )
        attempts.append(attempt)

    for attempt in attempts:
        db_session.add(attempt)
    await db_session.commit()
    return attempts