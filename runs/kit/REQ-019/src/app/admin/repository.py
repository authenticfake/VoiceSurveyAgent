"""
Admin configuration repository.

REQ-019: Admin configuration API
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import AuditLog, EmailConfig, ProviderConfig

logger = logging.getLogger(__name__)


class AdminConfigRepository:
    """Repository for admin configuration operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_provider_config(self) -> Optional[ProviderConfig]:
        """Get the current provider configuration (single-row pattern)."""
        result = await self.session.execute(
            select(ProviderConfig).order_by(ProviderConfig.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_or_create_provider_config(self) -> ProviderConfig:
        """Get existing provider config or create default one."""
        config = await self.get_provider_config()
        if config is None:
            config = ProviderConfig()
            self.session.add(config)
            await self.session.flush()
            logger.info(f"Created default provider config: {config.id}")
        return config

    async def update_provider_config(
        self, config: ProviderConfig, updates: Dict[str, Any]
    ) -> ProviderConfig:
        """Update provider configuration fields."""
        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        config.updated_at = datetime.utcnow()
        await self.session.flush()
        return config

    async def get_email_config(self, provider_config_id: UUID) -> Optional[EmailConfig]:
        """Get email configuration for a provider config."""
        result = await self.session.execute(
            select(EmailConfig).where(EmailConfig.provider_config_id == provider_config_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_email_config(self, provider_config_id: UUID) -> EmailConfig:
        """Get existing email config or create default one."""
        config = await self.get_email_config(provider_config_id)
        if config is None:
            config = EmailConfig(provider_config_id=provider_config_id)
            self.session.add(config)
            await self.session.flush()
            logger.info(f"Created default email config for provider: {provider_config_id}")
        return config

    async def update_email_config(
        self, config: EmailConfig, updates: Dict[str, Any]
    ) -> EmailConfig:
        """Update email configuration fields."""
        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        config.updated_at = datetime.utcnow()
        await self.session.flush()
        return config

    async def create_audit_log(
        self,
        user_id: UUID,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(audit_log)
        await self.session.flush()
        logger.info(f"Created audit log: {audit_log.id} - {action} on {resource_type}")
        return audit_log

    async def get_audit_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        resource_type: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> tuple[List[AuditLog], int]:
        """Get paginated audit logs with optional filters."""
        query = select(AuditLog)

        if resource_type:
            query = query.where(AuditLog.resource_type == resource_type)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        logs = list(result.scalars().all())

        return logs, total