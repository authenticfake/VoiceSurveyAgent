"""
Service tests for REQ-019: Admin configuration API
"""

import pytest
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import EmailConfig, ProviderConfig
from app.admin.schemas import (
    AdminConfigUpdate,
    EmailConfigUpdate,
    LLMConfigUpdate,
    RetentionConfigUpdate,
    TelephonyConfigUpdate,
)
from app.admin.secrets import MockSecretsManager
from app.admin.service import AdminConfigService
from app.auth.models import User


@pytest.mark.asyncio
class TestAdminConfigService:
    """Tests for AdminConfigService."""

    async def test_get_config_creates_default(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
    ):
        """Test that get_config creates default config if none exists."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        config = await service.get_config()

        assert config is not None
        assert config.telephony.provider_type.value == "telephony_api"
        assert config.llm.llm_provider.value == "openai"

    async def test_get_config_returns_existing(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test that get_config returns existing config."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        config = await service.get_config()

        assert config.id == provider_config.id
        assert config.telephony.provider_name == "twilio"

    async def test_update_config_telephony(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating telephony configuration."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        update = AdminConfigUpdate(
            telephony=TelephonyConfigUpdate(
                provider_name="telnyx",
                max_concurrent_calls=25,
            )
        )

        result = await service.update_config(
            update=update,
            user_id=admin_user.id,
        )

        assert result.telephony.provider_name == "telnyx"
        assert result.telephony.max_concurrent_calls == 25

    async def test_update_config_stores_credentials(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test that credentials are stored in Secrets Manager."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        update = AdminConfigUpdate(
            telephony=TelephonyConfigUpdate(
                api_key="new-api-key",
                api_secret="new-api-secret",
            )
        )

        await service.update_config(
            update=update,
            user_id=admin_user.id,
        )

        # Verify secrets were stored
        secrets = await mock_secrets_manager.get_secret("telephony-credentials")
        assert secrets["api_key"] == "new-api-key"
        assert secrets["api_secret"] == "new-api-secret"

    async def test_update_config_creates_audit_log(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test that config updates create audit log entries."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        update = AdminConfigUpdate(
            retention=RetentionConfigUpdate(
                recording_retention_days=365,
            )
        )

        await service.update_config(
            update=update,
            user_id=admin_user.id,
            ip_address="192.168.1.1",
            user_agent="Test Agent",
        )

        # Verify audit log was created
        logs_response = await service.get_audit_logs()
        assert logs_response.total >= 1

        # Find the update log
        update_logs = [
            log for log in logs_response.items
            if log.action == "config.update"
        ]
        assert len(update_logs) >= 1

        log = update_logs[0]
        assert log.user_id == admin_user.id
        assert "retention" in log.changes

    async def test_update_config_llm(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating LLM configuration."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        update = AdminConfigUpdate(
            llm=LLMConfigUpdate(
                llm_provider="anthropic",
                llm_model="claude-4.5-sonnet",
                api_key="anthropic-key",
            )
        )

        result = await service.update_config(
            update=update,
            user_id=admin_user.id,
        )

        assert result.llm.llm_provider.value == "anthropic"
        assert result.llm.llm_model == "claude-4.5-sonnet"

        # Verify API key was stored
        secrets = await mock_secrets_manager.get_secret("llm-credentials")
        assert secrets["api_key"] == "anthropic-key"

    async def test_update_config_email(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test updating email configuration."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        update = AdminConfigUpdate(
            email=EmailConfigUpdate(
                smtp_host="new-smtp.example.com",
                smtp_port=465,
                smtp_password="new-password",
            )
        )

        result = await service.update_config(
            update=update,
            user_id=admin_user.id,
        )

        assert result.email.smtp_host == "new-smtp.example.com"
        assert result.email.smtp_port == 465

        # Verify password was stored
        secrets = await mock_secrets_manager.get_secret("email-credentials")
        assert secrets["smtp_password"] == "new-password"

    async def test_get_audit_logs_pagination(
        self,
        db_session: AsyncSession,
        mock_secrets_manager: MockSecretsManager,
        admin_user: User,
        provider_config: ProviderConfig,
        email_config: EmailConfig,
    ):
        """Test audit log pagination."""
        service = AdminConfigService(
            session=db_session,
            secrets_manager=mock_secrets_manager,
        )

        # Create multiple audit logs
        for i in range(5):
            update = AdminConfigUpdate(
                retention=RetentionConfigUpdate(
                    recording_retention_days=100 + i,
                )
            )
            await service.update_config(
                update=update,
                user_id=admin_user.id,
            )

        # Test pagination
        result = await service.get_audit_logs(page=1, page_size=2)

        assert result.page == 1
        assert result.page_size == 2
        assert len(result.items) == 2
        assert result.total >= 5