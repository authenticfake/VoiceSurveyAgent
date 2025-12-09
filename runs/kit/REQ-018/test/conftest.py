"""
Pytest configuration and fixtures for REQ-018 tests.
"""

import asyncio
import os
from datetime import datetime, time
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.database import Base
from app.shared.models import (
    Campaign,
    CampaignLanguage,
    CampaignStatus,
    Contact,
    ContactState,
    ExportJob,
    ExportJobStatus,
    QuestionType,
    SurveyResponse,
    User,
    UserRole,
)


# Check if we should skip database tests
SKIP_DB_TESTS = os.environ.get("SKIP_DB_TESTS", "0") == "1"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test",
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
    if SKIP_DB_TESTS:
        pytest.skip("Database tests skipped (SKIP_DB_TESTS=1)")

    engine = create_async_engine(DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        oidc_sub="test|user001",
        email="testuser@example.com",
        name="Test User",
        role=UserRole.CAMPAIGN_MANAGER,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    user = User(
        id=uuid4(),
        oidc_sub="test|admin001",
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer user."""
    user = User(
        id=uuid4(),
        oidc_sub="test|viewer001",
        email="viewer@example.com",
        name="Viewer User",
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    """Create a test campaign."""
    campaign = Campaign(
        id=uuid4(),
        name="Test Campaign",
        description="A test campaign for export",
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
    )
    db_session.add(campaign)
    await db_session.flush()
    return campaign


@pytest_asyncio.fixture
async def test_contacts_with_responses(
    db_session: AsyncSession,
    test_campaign: Campaign,
) -> list[Contact]:
    """Create test contacts with various states and survey responses."""
    contacts = []

    # Completed contact with survey response
    completed_contact = Contact(
        id=uuid4(),
        campaign_id=test_campaign.id,
        external_contact_id="EXT001",
        phone_number="+14155551001",
        email="contact1@example.com",
        state=ContactState.COMPLETED,
        attempts_count=1,
        last_attempt_at=datetime.utcnow(),
    )
    db_session.add(completed_contact)
    contacts.append(completed_contact)

    # Add survey response for completed contact
    survey_response = SurveyResponse(
        id=uuid4(),
        contact_id=completed_contact.id,
        campaign_id=test_campaign.id,
        call_attempt_id=uuid4(),  # Mock call attempt ID
        q1_answer="8",
        q2_answer="Better mobile app",
        q3_answer="9",
        completed_at=datetime.utcnow(),
    )
    db_session.add(survey_response)

    # Refused contact
    refused_contact = Contact(
        id=uuid4(),
        campaign_id=test_campaign.id,
        external_contact_id="EXT002",
        phone_number="+14155551002",
        email="contact2@example.com",
        state=ContactState.REFUSED,
        attempts_count=1,
        last_attempt_at=datetime.utcnow(),
    )
    db_session.add(refused_contact)
    contacts.append(refused_contact)

    # Not reached contact
    not_reached_contact = Contact(
        id=uuid4(),
        campaign_id=test_campaign.id,
        external_contact_id="EXT003",
        phone_number="+14155551003",
        state=ContactState.NOT_REACHED,
        attempts_count=3,
        last_attempt_at=datetime.utcnow(),
    )
    db_session.add(not_reached_contact)
    contacts.append(not_reached_contact)

    # Pending contact (should not be in export)
    pending_contact = Contact(
        id=uuid4(),
        campaign_id=test_campaign.id,
        external_contact_id="EXT004",
        phone_number="+14155551004",
        state=ContactState.PENDING,
        attempts_count=0,
    )
    db_session.add(pending_contact)
    contacts.append(pending_contact)

    # In progress contact (should not be in export)
    in_progress_contact = Contact(
        id=uuid4(),
        campaign_id=test_campaign.id,
        phone_number="+14155551005",
        state=ContactState.IN_PROGRESS,
        attempts_count=1,
    )
    db_session.add(in_progress_contact)
    contacts.append(in_progress_contact)

    await db_session.flush()
    return contacts