from __future__ import annotations

import os
from typing import Callable, Iterable, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.admin.domain.models import (
    AdminConfigurationUpdateRequest,
    AdminConfigurationView,
    EmailProviderSettingsModel,
    EmailTemplateModel,
    ProviderConfigModel,
)
from app.admin.domain.repository import AdminConfigRepository
from app.admin.services.audit import AuditLogRecord, AuditLogger, StructuredAuditLogger
from app.auth.domain.models import Role, UserPrincipal


class EmailProviderSettingsReader:
    """Protocol-like base for retrieving email provider settings."""

    def read(self) -> EmailProviderSettingsModel:  # pragma: no cover - interface
        raise NotImplementedError


class EnvEmailProviderSettingsReader(EmailProviderSettingsReader):
    """Reads email provider settings from environment variables."""

    def __init__(self, env: Optional[dict[str, str]] = None) -> None:
        self._env = env or os.environ

    def read(self) -> EmailProviderSettingsModel:
        return EmailProviderSettingsModel(
            provider=self._env.get("EMAIL_PROVIDER", "ses"),
            from_email=self._env.get("EMAIL_FROM_ADDRESS"),
            reply_to_email=self._env.get("EMAIL_REPLY_TO"),
            region=self._env.get("EMAIL_PROVIDER_REGION"),
        )


class AdminConfigService:
    """Coordinates provider configuration, retention settings, and templates."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        audit_logger: Optional[AuditLogger] = None,
        email_provider_reader: Optional[EmailProviderSettingsReader] = None,
        repository_factory: Optional[
            Callable[[Session], AdminConfigRepository]
        ] = None,
    ) -> None:
        self._session_factory = session_factory
        self._audit_logger = audit_logger or StructuredAuditLogger()
        self._email_provider_reader = (
            email_provider_reader or EnvEmailProviderSettingsReader()
        )
        self._repository_factory = repository_factory or AdminConfigRepository

    def get_configuration(self) -> AdminConfigurationView:
        with self._session_factory() as session:
            repo = self._repository_factory(session)
            provider = repo.get_provider_configuration()
            email_templates = repo.list_email_templates()
        return self._build_view(
            provider_model=repo.to_provider_model(provider),
            templates=repo.to_template_models(email_templates),
        )

    def update_configuration(
        self,
        payload: AdminConfigurationUpdateRequest,
        principal: UserPrincipal,
    ) -> AdminConfigurationView:
        with self._session_factory() as session:
            repo = self._repository_factory(session)
            provider_entity = repo.get_provider_configuration(
                for_update=True, create_if_missing=True
            )
            provider_changes = repo.update_provider_configuration(
                provider_entity,
                provider_payload=payload.provider,
                retention_payload=payload.retention,
            )
            template_changes = []
            if payload.email_templates:
                template_changes = repo.update_email_templates(payload.email_templates)
            session.commit()
            provider_model = repo.to_provider_model(provider_entity)
            templates = repo.to_template_models(repo.list_email_templates())
        if provider_changes or template_changes:
            self._audit_logger.record(
                AuditLogRecord(
                    action="admin.config.updated",
                    actor_id=principal.user_id,
                    actor_email=principal.email,
                    changes={
                        "provider": provider_changes,
                        "templates": template_changes,
                    },
                    metadata={"role": principal.role.value},
                )
            )
        return self._build_view(
            provider_model=provider_model,
            templates=templates,
        )

    def _build_view(
        self,
        *,
        provider_model: ProviderConfigModel,
        templates: Iterable[EmailTemplateModel],
    ) -> AdminConfigurationView:
        retention = {
            "recording_retention_days": provider_model.recording_retention_days,
            "transcript_retention_days": provider_model.transcript_retention_days,
        }
        return AdminConfigurationView(
            provider=provider_model,
            retention=retention,
            email_provider=self._email_provider_reader.read(),
            email_templates=list(templates),
        )