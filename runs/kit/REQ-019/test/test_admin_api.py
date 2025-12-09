"""
API tests for REQ-019: Admin configuration API
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.admin.models import EmailConfig, ProviderConfig
from app.admin.secrets import MockSecretsManager
from app.auth.models import User


@pytest.mark.asyncio
class TestGetConfig:
    """Tests for GET /api/admin/config endpoint."""

    async def test_get_config_success(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test successful config retrieval by admin."""
        response = await test_client.get(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "id" in data
        assert "telephony" in data
        assert "llm" in data
        assert "email" in data
        assert "retention" in data

        # Verify telephony config
        assert data["telephony"]["provider_type"] == "telephony_api"
        assert data["telephony"]["provider_name"] == "twilio"
        assert data["telephony"]["max_concurrent_calls"] == 10

        # Verify LLM config
        assert data["llm"]["llm_provider"] == "openai"
        assert data["llm"]["llm_model"] == "gpt-4.1-mini"

        # Verify retention config
        assert data["retention"]["recording_retention_days"] == 180
        assert data["retention"]["transcript_retention_days"] == 180

    async def test_get_config_creates_default_if_missing(
        self,
        test_client: AsyncClient,
        admin_user: User,
    ):
        """Test that default config is created if none exists."""
        response = await test_client.get(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have default values
        assert data["telephony"]["provider_type"] == "telephony_api"
        assert data["llm"]["llm_provider"] == "openai"

    async def test_get_config_requires_admin_role(
        self,
        test_client: AsyncClient,
        viewer_user: User,
    ):
        """Test that non-admin users cannot access config."""
        response = await test_client.get(
            "/api/admin/config",
            headers={
                "X-User-ID": str(viewer_user.id),
                "X-User-Role": "viewer",
            },
        )

        assert response.status_code == 403

    async def test_get_config_requires_user_id(
        self,
        test_client: AsyncClient,
    ):
        """Test that user ID is required."""
        response = await test_client.get(
            "/api/admin/config",
            headers={
                "X-User-Role": "admin",
            },
        )

        assert response.status_code == 403


@pytest.mark.asyncio
class TestUpdateConfig:
    """Tests for PUT /api/admin/config endpoint."""

    async def test_update_telephony_config(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating telephony configuration."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "telephony": {
                    "provider_name": "telnyx",
                    "max_concurrent_calls": 20,
                }
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["telephony"]["provider_name"] == "telnyx"
        assert data["telephony"]["max_concurrent_calls"] == 20

    async def test_update_llm_config(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating LLM configuration."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "llm": {
                    "llm_provider": "anthropic",
                    "llm_model": "claude-4.5-sonnet",
                }
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["llm"]["llm_provider"] == "anthropic"
        assert data["llm"]["llm_model"] == "claude-4.5-sonnet"

    async def test_update_email_config(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating email configuration."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "email": {
                    "smtp_host": "smtp.newhost.com",
                    "smtp_port": 465,
                    "from_email": "new@example.com",
                }
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"]["smtp_host"] == "smtp.newhost.com"
        assert data["email"]["smtp_port"] == 465
        assert data["email"]["from_email"] == "new@example.com"

    async def test_update_retention_config(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating retention configuration."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "retention": {
                    "recording_retention_days": 365,
                    "transcript_retention_days": 90,
                }
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["retention"]["recording_retention_days"] == 365
        assert data["retention"]["transcript_retention_days"] == 90

    async def test_update_stores_credentials_in_secrets_manager(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
        mock_secrets_manager: MockSecretsManager,
    ):
        """Test that credentials are stored in Secrets Manager."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "telephony": {
                    "api_key": "test-api-key",
                    "api_secret": "test-api-secret",
                }
            },
        )

        assert response.status_code == 200

        # Verify credentials were stored in secrets manager
        secrets = await mock_secrets_manager.get_secret("telephony-credentials")
        assert secrets["api_key"] == "test-api-key"
        assert secrets["api_secret"] == "test-api-secret"

    async def test_update_requires_admin_role(
        self,
        test_client: AsyncClient,
        viewer_user: User,
    ):
        """Test that non-admin users cannot update config."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(viewer_user.id),
                "X-User-Role": "viewer",
            },
            json={
                "telephony": {
                    "max_concurrent_calls": 50,
                }
            },
        )

        assert response.status_code == 403

    async def test_update_validates_email_format(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test that invalid email format is rejected."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "email": {
                    "from_email": "invalid-email",
                }
            },
        )

        assert response.status_code == 422  # Validation error

    async def test_update_validates_retention_days_range(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test that retention days must be within valid range."""
        response = await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "retention": {
                    "recording_retention_days": 5000,  # Exceeds max of 3650
                }
            },
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuditLogs:
    """Tests for GET /api/admin/audit-logs endpoint."""

    async def test_get_audit_logs_success(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test successful audit log retrieval."""
        # First make a config update to create an audit log
        await test_client.put(
            "/api/admin/config",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
            json={
                "telephony": {
                    "max_concurrent_calls": 15,
                }
            },
        )

        # Then retrieve audit logs
        response = await test_client.get(
            "/api/admin/audit-logs",
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

        # Should have at least one audit log entry
        assert len(data["items"]) >= 1

    async def test_get_audit_logs_pagination(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test audit log pagination."""
        response = await test_client.get(
            "/api/admin/audit-logs",
            params={"page": 1, "page_size": 10},
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 10

    async def test_get_audit_logs_filter_by_resource_type(
        self,
        test_client: AsyncClient,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test filtering audit logs by resource type."""
        response = await test_client.get(
            "/api/admin/audit-logs",
            params={"resource_type": "admin_config"},
            headers={
                "X-User-ID": str(admin_user.id),
                "X-User-Role": "admin",
            },
        )

        assert response.status_code == 200

    async def test_get_audit_logs_requires_admin_role(
        self,
        test_client: AsyncClient,
        viewer_user: User,
    ):
        """Test that non-admin users cannot access audit logs."""
        response = await test_client.get(
            "/api/admin/audit-logs",
            headers={
                "X-User-ID": str(viewer_user.id),
                "X-User-Role": "viewer",
            },
        )

        assert response.status_code == 403