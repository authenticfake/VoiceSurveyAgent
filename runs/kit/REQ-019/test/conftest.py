"""
Test fixtures for REQ-019: Admin configuration API
"""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.admin.models import AuditLog, EmailConfig, ProviderConfig
from app.admin.secrets import MockSecretsManager, SecretsManagerInterface
from app.auth.models import User, UserRole
from app.shared.database import Base, get_db_session


# Test database URL - use environment variable or default to test database
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def mock_secrets_manager() -> MockSecretsManager:
    """Create mock secrets manager for testing."""
    return MockSecretsManager()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user for testing."""
    user = User(
        id=uuid4(),
        oidc_sub="oidc|test-admin",
        email="admin@test.com",
        name="Test Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create a viewer user for testing."""
    user = User(
        id=uuid4(),
        oidc_sub="oidc|test-viewer",
        email="viewer@test.com",
        name="Test Viewer",
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def provider_config(db_session: AsyncSession) -> ProviderConfig:
    """Create a provider config for testing."""
    config = ProviderConfig(
        id=uuid4(),
        provider_type="telephony_api",
        provider_name="twilio",
        outbound_number="+14155550100",
        max_concurrent_calls=10,
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        recording_retention_days=180,
        transcript_retention_days=180,
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest_asyncio.fixture
async def email_config(db_session: AsyncSession, provider_config: ProviderConfig) -> EmailConfig:
    """Create an email config for testing."""
    config = EmailConfig(
        id=uuid4(),
        provider_config_id=provider_config.id,
        smtp_host="smtp.test.com",
        smtp_port=587,
        smtp_username="test@test.com",
        from_email="noreply@test.com",
        from_name="Test Survey",
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


def create_test_app(db_session: AsyncSession, secrets_manager: SecretsManagerInterface):
    """Create test FastAPI application with injected dependencies."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    from app.admin.router import router as admin_router
    from app.shared.exceptions import AppException

    app = FastAPI()

    # Override dependencies
    async def override_get_db_session():
        yield db_session

    async def override_get_secrets_manager():
        return secrets_manager

    app.dependency_overrides[get_db_session] = override_get_db_session

    # Import and override secrets manager dependency
    from app.admin import secrets
    app.dependency_overrides[secrets.get_secrets_manager] = override_get_secrets_manager

    # Exception handler
    @app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
        )

    app.include_router(admin_router)

    return app


@pytest_asyncio.fixture
async def test_client(
    db_session: AsyncSession,
    mock_secrets_manager: MockSecretsManager,
) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    app = create_test_app(db_session, mock_secrets_manager)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client