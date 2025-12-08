from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin.domain.errors import (
    EmailTemplateNotFoundError,
    ProviderConfigurationNotFoundError,
)
from app.admin.domain.models import (
    EmailTemplateModel,
    EmailTemplateUpdateModel,
    ProviderConfigModel,
    ProviderConfigUpdateModel,
    RetentionSettingsModel,
)
from app.infra.db import models as db_models


class AdminConfigRepository:
    """Data-access facade for provider configuration and templates."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_provider_configuration(
        self,
        *,
        for_update: bool = False,
        create_if_missing: bool = False,
    ) -> db_models.ProviderConfiguration:
        stmt = select(db_models.ProviderConfiguration).limit(1)
        if for_update:
            stmt = stmt.with_for_update()
        entity = self._session.execute(stmt).scalars().first()
        if entity is None:
            if not create_if_missing:
                raise ProviderConfigurationNotFoundError(
                    "Provider configuration row is missing. Seed data should include a default entry."
                )
            entity = db_models.ProviderConfiguration(
                provider_type="telephony_api",
                provider_name="unset",
                outbound_number="+10000000000",
                max_concurrent_calls=1,
                llm_provider="openai",
                llm_model="gpt-4.1-mini",
                recording_retention_days=180,
                transcript_retention_days=180,
            )
            self._session.add(entity)
            self._session.flush()
        return entity

    def list_email_templates(self) -> List[db_models.EmailTemplate]:
        stmt = select(db_models.EmailTemplate).order_by(
            db_models.EmailTemplate.type, db_models.EmailTemplate.locale
        )
        return list(self._session.execute(stmt).scalars())

    def to_provider_model(
        self, entity: db_models.ProviderConfiguration
    ) -> ProviderConfigModel:
        return ProviderConfigModel(
            id=entity.id,
            provider_type=entity.provider_type,
            provider_name=entity.provider_name,
            outbound_number=entity.outbound_number,
            max_concurrent_calls=entity.max_concurrent_calls,
            llm_provider=entity.llm_provider,
            llm_model=entity.llm_model,
            recording_retention_days=entity.recording_retention_days,
            transcript_retention_days=entity.transcript_retention_days,
        )

    def to_template_models(
        self, records: Iterable[db_models.EmailTemplate]
    ) -> List[EmailTemplateModel]:
        return [
            EmailTemplateModel(
                id=record.id,
                name=record.name,
                type=record.type,
                locale=record.locale,
                subject=record.subject,
                body_html=record.body_html,
                body_text=record.body_text,
            )
            for record in records
        ]

    def update_provider_configuration(
        self,
        entity: db_models.ProviderConfiguration,
        provider_payload: ProviderConfigUpdateModel,
        retention_payload: RetentionSettingsModel,
    ) -> dict:
        now = datetime.now(timezone.utc)
        changes: dict = {}
        mapping = {
            "provider_type": provider_payload.provider_type.value,
            "provider_name": provider_payload.provider_name,
            "outbound_number": provider_payload.outbound_number,
            "max_concurrent_calls": provider_payload.max_concurrent_calls,
            "llm_provider": provider_payload.llm_provider.value,
            "llm_model": provider_payload.llm_model,
            "recording_retention_days": retention_payload.recording_retention_days,
            "transcript_retention_days": retention_payload.transcript_retention_days,
        }
        for field_name, new_value in mapping.items():
            current_value = getattr(entity, field_name)
            if current_value != new_value:
                changes[field_name] = {"old": current_value, "new": new_value}
                setattr(entity, field_name, new_value)
        if changes:
            entity.updated_at = now
        return changes

    def update_email_templates(
        self, updates: Iterable[EmailTemplateUpdateModel]
    ) -> List[dict]:
        change_log: List[dict] = []
        now = datetime.now(timezone.utc)
        for payload in updates:
            record = self._session.get(db_models.EmailTemplate, payload.id)
            if record is None:
                raise EmailTemplateNotFoundError(
                    f"Email template {payload.id} not found."
                )
            for field_name in ("name", "subject", "body_html", "body_text"):
                new_value = getattr(payload, field_name)
                if new_value is None:
                    continue
                current_value = getattr(record, field_name)
                if current_value != new_value:
                    change_log.append(
                        {
                            "template_id": str(record.id),
                            "field": field_name,
                            "old": current_value,
                            "new": new_value,
                        }
                    )
                    setattr(record, field_name, new_value)
            if change_log:
                record.updated_at = now
        return change_log