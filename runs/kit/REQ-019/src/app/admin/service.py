"""
Admin configuration service.

REQ-019: Admin configuration API
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog, EmailConfig, ProviderConfig
from app.admin.repository import AdminConfigRepository
from app.admin.schemas import (
    AdminConfigResponse,
    AdminConfigUpdate,
    AuditLogEntry,
    AuditLogListResponse,
    EmailConfigResponse,
    LLMConfigResponse,
    RetentionConfigResponse,
    TelephonyConfigResponse,
)
from app.admin.secrets import SecretsManagerInterface
from app.shared.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Secret names for different credential types
TELEPHONY_SECRETS_KEY = "telephony-credentials"
LLM_SECRETS_KEY = "llm-credentials"
EMAIL_SECRETS_KEY = "email-credentials"


class AdminConfigService:
    """Service for admin configuration operations."""

    def __init__(
        self,
        session: AsyncSession,
        secrets_manager: SecretsManagerInterface,
    ):
        self.repository = AdminConfigRepository(session)
        self.secrets_manager = secrets_manager
        self.session = session

    async def get_config(self) -> AdminConfigResponse:
        """Get the current admin configuration."""
        provider_config = await self.repository.get_or_create_provider_config()
        email_config = await self.repository.get_or_create_email_config(provider_config.id)

        return self._build_config_response(provider_config, email_config)

    async def update_config(
        self,
        update: AdminConfigUpdate,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AdminConfigResponse:
        """Update admin configuration with audit logging."""
        provider_config = await self.repository.get_or_create_provider_config()
        email_config = await self.repository.get_or_create_email_config(provider_config.id)

        changes: Dict[str, Any] = {}

        # Update telephony config
        if update.telephony:
            telephony_changes = await self._update_telephony_config(
                provider_config, update.telephony.model_dump(exclude_none=True)
            )
            if telephony_changes:
                changes["telephony"] = telephony_changes

        # Update LLM config
        if update.llm:
            llm_changes = await self._update_llm_config(
                provider_config, update.llm.model_dump(exclude_none=True)
            )
            if llm_changes:
                changes["llm"] = llm_changes

        # Update email config
        if update.email:
            email_changes = await self._update_email_config(
                email_config, update.email.model_dump(exclude_none=True)
            )
            if email_changes:
                changes["email"] = email_changes

        # Update retention config
        if update.retention:
            retention_changes = await self._update_retention_config(
                provider_config, update.retention.model_dump(exclude_none=True)
            )
            if retention_changes:
                changes["retention"] = retention_changes

        # Create audit log if there were changes
        if changes:
            await self.repository.create_audit_log(
                user_id=user_id,
                action="config.update",
                resource_type="admin_config",
                resource_id=provider_config.id,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        return self._build_config_response(provider_config, email_config)

    async def _update_telephony_config(
        self, config: ProviderConfig, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update telephony configuration and store credentials in Secrets Manager."""
        changes = {}

        # Extract credentials for Secrets Manager
        credentials = {}
        credential_fields = ["api_key", "api_secret", "account_sid"]
        for field in credential_fields:
            if field in updates:
                credentials[field] = updates.pop(field)
                changes[field] = "***REDACTED***"

        # Store credentials in Secrets Manager if any provided
        if credentials:
            existing_secrets = await self.secrets_manager.get_secret(TELEPHONY_SECRETS_KEY)
            existing_secrets.update(credentials)
            await self.secrets_manager.put_secret(TELEPHONY_SECRETS_KEY, existing_secrets)

        # Update database fields
        db_fields = ["provider_type", "provider_name", "outbound_number", "max_concurrent_calls"]
        db_updates = {k: v for k, v in updates.items() if k in db_fields}

        if db_updates:
            for key, value in db_updates.items():
                old_value = getattr(config, key)
                if old_value != value:
                    changes[key] = {"old": str(old_value), "new": str(value)}

            await self.repository.update_provider_config(config, db_updates)

        return changes

    async def _update_llm_config(
        self, config: ProviderConfig, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update LLM configuration and store credentials in Secrets Manager."""
        changes = {}

        # Extract API key for Secrets Manager
        if "api_key" in updates:
            api_key = updates.pop("api_key")
            existing_secrets = await self.secrets_manager.get_secret(LLM_SECRETS_KEY)
            existing_secrets["api_key"] = api_key
            await self.secrets_manager.put_secret(LLM_SECRETS_KEY, existing_secrets)
            changes["api_key"] = "***REDACTED***"

        # Update database fields
        db_fields = ["llm_provider", "llm_model"]
        db_updates = {k: v for k, v in updates.items() if k in db_fields}

        if db_updates:
            for key, value in db_updates.items():
                old_value = getattr(config, key)
                if old_value != value:
                    changes[key] = {"old": str(old_value), "new": str(value)}

            await self.repository.update_provider_config(config, db_updates)

        return changes

    async def _update_email_config(
        self, config: EmailConfig, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update email configuration and store credentials in Secrets Manager."""
        changes = {}

        # Extract password for Secrets Manager
        if "smtp_password" in updates:
            password = updates.pop("smtp_password")
            existing_secrets = await self.secrets_manager.get_secret(EMAIL_SECRETS_KEY)
            existing_secrets["smtp_password"] = password
            await self.secrets_manager.put_secret(EMAIL_SECRETS_KEY, existing_secrets)
            changes["smtp_password"] = "***REDACTED***"

        # Update database fields
        db_fields = ["smtp_host", "smtp_port", "smtp_username", "from_email", "from_name"]
        db_updates = {k: v for k, v in updates.items() if k in db_fields}

        if db_updates:
            for key, value in db_updates.items():
                old_value = getattr(config, key)
                if old_value != value:
                    changes[key] = {"old": str(old_value) if old_value else None, "new": str(value)}

            await self.repository.update_email_config(config, db_updates)

        return changes

    async def _update_retention_config(
        self, config: ProviderConfig, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update retention configuration."""
        changes = {}

        db_fields = ["recording_retention_days", "transcript_retention_days"]
        db_updates = {k: v for k, v in updates.items() if k in db_fields}

        if db_updates:
            for key, value in db_updates.items():
                old_value = getattr(config, key)
                if old_value != value:
                    changes[key] = {"old": old_value, "new": value}

            await self.repository.update_provider_config(config, db_updates)

        return changes

    async def get_audit_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        resource_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> AuditLogListResponse:
        """Get paginated audit logs."""
        logs, total = await self.repository.get_audit_logs(
            page=page,
            page_size=page_size,
            resource_type=resource_type,
            user_id=user_id,
        )

        items = []
        for log in logs:
            items.append(
                AuditLogEntry(
                    id=log.id,
                    user_id=log.user_id,
                    user_email=log.user.email if log.user else "unknown",
                    action=log.action,
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    changes=log.changes,
                    ip_address=log.ip_address,
                    user_agent=log.user_agent,
                    timestamp=log.created_at,
                )
            )

        total_pages = (total + page_size - 1) // page_size

        return AuditLogListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def _build_config_response(
        self, provider_config: ProviderConfig, email_config: EmailConfig
    ) -> AdminConfigResponse:
        """Build the admin config response from database models."""
        return AdminConfigResponse(
            id=provider_config.id,
            telephony=TelephonyConfigResponse(
                provider_type=provider_config.provider_type,
                provider_name=provider_config.provider_name,
                outbound_number=provider_config.outbound_number,
                max_concurrent_calls=provider_config.max_concurrent_calls,
            ),
            llm=LLMConfigResponse(
                llm_provider=provider_config.llm_provider,
                llm_model=provider_config.llm_model,
            ),
            email=EmailConfigResponse(
                smtp_host=email_config.smtp_host,
                smtp_port=email_config.smtp_port,
                smtp_username=email_config.smtp_username,
                from_email=email_config.from_email,
                from_name=email_config.from_name,
            ),
            retention=RetentionConfigResponse(
                recording_retention_days=provider_config.recording_retention_days,
                transcript_retention_days=provider_config.transcript_retention_days,
            ),
            created_at=provider_config.created_at,
            updated_at=provider_config.updated_at,
        )