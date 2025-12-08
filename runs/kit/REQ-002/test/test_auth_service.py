"""
Tests for authentication service.

Tests OIDC flow, JWT validation, and user management.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenPayload, UserRole
from app.auth.service import AuthService
from app.campaigns.models import User, UserRoleEnum
from app.config import Settings
from app.shared.exceptions import AuthenticationError, ConfigurationError


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    return Settings(
        database_url="postgresql://test:test@localhost:5432/test",
        oidc_issuer="https://auth.example.com",
        oidc_client_id="test-client",
        oidc_client_secret="test-secret",
        oidc_redirect_uri="http://localhost:8000/api/auth/callback",
        jwt_secret_key="test-secret-key-for-testing-only",
        jwt_algorithm="HS256",
        jwt_expiration_minutes=60,
        jwt_issuer="voicesurveyagent",
        jwt_audience="voicesurveyagent-api",
    )


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Create mock HTTP client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    return client


@pytest.fixture
def oidc_discovery_response() -> dict:
    """OIDC discovery document response."""
    return {
        "issuer": "https://auth.example.com",
        "authorization_endpoint": "https://auth.example.com/authorize",
        "token_endpoint": "https://auth.example.com/token",
        "userinfo_endpoint": "https://auth.example.com/userinfo",
        "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
    }


class TestAuthServiceInitialization:
    """Tests for AuthService initialization."""

    @pytest.mark.asyncio
    async def test_initialize_success(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
        mock_http_client: AsyncMock,
        oidc_discovery_response: dict,
    ) -> None:
        """Test successful OIDC initialization."""
        mock_response = MagicMock()
        mock_response.json.return_value = oidc_discovery_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
            http_client=mock_http_client,
        )

        with patch("app.auth.service.PyJWKClient"):
            await service.initialize()

        mock_http_client.get.assert_called_once_with(
            "https://auth.example.com/.well-known/openid-configuration"
        )
        assert service._oidc_config is not None
        assert str(service._oidc_config.issuer) == "https://auth.example.com/"

    @pytest.mark.asyncio
    async def test_initialize_no_issuer(
        self,
        mock_db_session: AsyncMock,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test initialization fails without OIDC issuer."""
        settings = Settings(
            database_url="postgresql://test:test@localhost:5432/test",
            oidc_issuer=None,
        )

        service = AuthService(
            settings=settings,
            db_session=mock_db_session,
            http_client=mock_http_client,
        )

        with pytest.raises(ConfigurationError) as exc_info:
            await service.initialize()

        assert "OIDC issuer not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_http_error(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test initialization handles HTTP errors."""
        mock_http_client.get.side_effect = httpx.HTTPError("Connection failed")

        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
            http_client=mock_http_client,
        )

        with pytest.raises(ConfigurationError) as exc_info:
            await service.initialize()

        assert "Failed to fetch OIDC configuration" in str(exc_info.value)


class TestAuthorizationUrl:
    """Tests for authorization URL generation."""

    @pytest.mark.asyncio
    async def test_generate_authorization_url(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
        mock_http_client: AsyncMock,
        oidc_discovery_response: dict,
    ) -> None:
        """Test authorization URL generation."""
        mock_response = MagicMock()
        mock_response.json.return_value = oidc_discovery_response
        mock_response.raise_for_status = MagicMock()
        mock_http_client.get.return_value = mock_response

        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
            http_client=mock_http_client,
        )

        with patch("app.auth.service.PyJWKClient"):
            await service.initialize()

        auth_url, state = service.generate_authorization_url()

        assert "https://auth.example.com/authorize" in auth_url
        assert "client_id=test-client" in auth_url
        assert "response_type=code" in auth_url
        assert f"state={state}" in auth_url
        assert len(state) > 20  # State should be sufficiently random

    @pytest.mark.asyncio
    async def test_generate_authorization_url_not_initialized(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
        mock_http_client: AsyncMock,
    ) -> None:
        """Test authorization URL fails if not initialized."""
        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
            http_client=mock_http_client,
        )

        with pytest.raises(ConfigurationError) as exc_info:
            service.generate_authorization_url()

        assert "OIDC not initialized" in str(exc_info.value)


class TestSessionTokenValidation:
    """Tests for session token validation."""

    def test_validate_session_token_success(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test successful session token validation."""
        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
        )

        # Create a valid token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test-user-sub",
            "iat": now.timestamp(),
            "exp": (now + timedelta(hours=1)).timestamp(),
            "iss": "voicesurveyagent",
            "aud": "voicesurveyagent-api",
            "email": "test@example.com",
            "name": "Test User",
            "role": "viewer",
        }
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm="HS256")

        result = service.validate_session_token(token)

        assert result.sub == "test-user-sub"
        assert result.email == "test@example.com"
        assert result.role == UserRole.VIEWER

    def test_validate_session_token_expired(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test expired token validation."""
        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
        )

        # Create an expired token
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test-user-sub",
            "iat": (now - timedelta(hours=2)).timestamp(),
            "exp": (now - timedelta(hours=1)).timestamp(),
            "iss": "voicesurveyagent",
            "aud": "voicesurveyagent-api",
        }
        token = jwt.encode(payload, mock_settings.jwt_secret_key, algorithm="HS256")

        with pytest.raises(AuthenticationError) as exc_info:
            service.validate_session_token(token)

        assert "Token has expired" in str(exc_info.value)

    def test_validate_session_token_invalid(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test invalid token validation."""
        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
        )

        with pytest.raises(AuthenticationError) as exc_info:
            service.validate_session_token("invalid-token")

        assert "Invalid token" in str(exc_info.value)


class TestUserManagement:
    """Tests for user management."""

    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test getting user by ID."""
        user_id = uuid4()
        mock_user = User(
            id=user_id,
            oidc_sub="test-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.VIEWER,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
        )

        result = await service.get_user_by_id(user_id)

        assert result is not None
        assert result.id == user_id
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_oidc_sub(
        self,
        mock_settings: Settings,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test getting user by OIDC subject."""
        mock_user = User(
            id=uuid4(),
            oidc_sub="test-sub",
            email="test@example.com",
            name="Test User",
            role=UserRoleEnum.VIEWER,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        service = AuthService(
            settings=mock_settings,
            db_session=mock_db_session,
        )

        result = await service.get_user_by_oidc_sub("test-sub")

        assert result is not None
        assert result.oidc_sub == "test-sub"