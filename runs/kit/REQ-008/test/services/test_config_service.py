from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.admin.domain.models import (
    AdminConfigurationUpdateRequest,
    EmailProviderSettingsModel,
    EmailTemplateModel,
    EmailTemplateUpdateModel,
    ProviderConfigModel,
    ProviderConfigUpdateModel,
    RetentionSettingsModel,
)
from app.admin.domain.repository import AdminConfigRepository
from app.admin.services.audit import AuditLogRecord
from app.admin.services.config_service import AdminConfigService
from app.auth.domain.models import Role
from app.auth.domain.models import UserPrincipal


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def commit(self):
        self.committed = True

    def flush(self):
        self.flushed = True


def _build_provider_entity() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        provider_type="telephony_api",
        provider_name="twilio",
        outbound_number="+12065550100",
        max_concurrent_calls=10,
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        recording_retention_days=180,
        transcript_retention_days=180,
        updated_at=None,
    )


def _build_template_entity() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name="Completed EN",
        type="completed",
        locale="en",
        subject="Thanks",
        body_html="<p>Thanks</p>",
        body_text=None,
        updated_at=None,
    )


class StubEmailProviderReader:
    def __init__(self):
        self._value = EmailProviderSettingsModel(
            provider="ses", from_email="noreply@example.com", reply_to_email=None, region="eu-central-1"
        )

    def read(self) -> EmailProviderSettingsModel:
        return self._value


class SpyAuditLogger:
    def __init__(self):
        self.records: list[AuditLogRecord] = []

    def record(self, record: AuditLogRecord) -> None:
        self.records.append(record)


def test_get_configuration_returns_snapshot(monkeypatch):
    provider_entity = _build_provider_entity()
    template_entity = _build_template_entity()

    repo = SimpleNamespace(
        get_provider_configuration=lambda **kwargs: provider_entity,
        list_email_templates=lambda: [template_entity],
        to_provider_model=lambda entity: ProviderConfigModel(
            id=entity.id,
            provider_type=entity.provider_type,
            provider_name=entity.provider_name,
            outbound_number=entity.outbound_number,
            max_concurrent_calls=entity.max_concurrent_calls,
            llm_provider=entity.llm_provider,
            llm_model=entity.llm_model,
            recording_retention_days=entity.recording_retention_days,
            transcript_retention_days=entity.transcript_retention_days,
        ),
        to_template_models=lambda _: [
            EmailTemplateModel(
                id=template_entity.id,
                name=template_entity.name,
                type=template_entity.type,
                locale=template_entity.locale,
                subject=template_entity.subject,
                body_html=template_entity.body_html,
                body_text=template_entity.body_text,
            )
        ],
    )
    session_factory = lambda: DummySession()
    service = AdminConfigService(
        session_factory=session_factory,
        audit_logger=SpyAuditLogger(),
        email_provider_reader=StubEmailProviderReader(),
        repository_factory=lambda _: repo,
    )

    snapshot = service.get_configuration()

    assert snapshot.provider.provider_name == "twilio"
    assert snapshot.retention.recording_retention_days == 180
    assert len(snapshot.email_templates) == 1
    assert snapshot.email_provider.provider == "ses"


def test_update_configuration_persists_changes_and_audits():
    provider_entity = _build_provider_entity()
    template_entity = _build_template_entity()
    repo = SimpleNamespace()
    repo.get_provider_configuration = lambda **kwargs: provider_entity
    repo.list_email_templates = lambda: [template_entity]
    repo.to_provider_model = lambda entity: ProviderConfigModel(
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
    repo.to_template_models = lambda _: [
        EmailTemplateModel(
            id=template_entity.id,
            name=template_entity.name,
            type=template_entity.type,
            locale=template_entity.locale,
            subject=template_entity.subject,
            body_html=template_entity.body_html,
            body_text=template_entity.body_text,
        )
    ]

    def update_provider_configuration(entity, provider_payload, retention_payload):
        entity.max_concurrent_calls = provider_payload.max_concurrent_calls
        entity.recording_retention_days = retention_payload.recording_retention_days
        return {"max_concurrent_calls": {"old": 10, "new": 15}}

    repo.update_provider_configuration = update_provider_configuration

    def update_email_templates(payloads):
        template_entity.subject = payloads[0].subject
        return [{"template_id": str(template_entity.id), "field": "subject"}]

    repo.update_email_templates = update_email_templates

    session_factory = lambda: DummySession()
    audit_logger = SpyAuditLogger()
    service = AdminConfigService(
        session_factory=session_factory,
        audit_logger=audit_logger,
        email_provider_reader=StubEmailProviderReader(),
        repository_factory=lambda _: repo,
    )

    principal = UserPrincipal(user_id=uuid4(), email="admin@example.com", role=Role.admin)
    payload = AdminConfigurationUpdateRequest(
        provider=ProviderConfigUpdateModel(
            provider_type="telephony_api",
            provider_name="twilio",
            outbound_number="+12065550100",
            max_concurrent_calls=15,
            llm_provider="openai",
            llm_model="gpt-4.1-mini",
        ),
        retention=RetentionSettingsModel(recording_retention_days=365, transcript_retention_days=365),
        email_templates=[EmailTemplateUpdateModel(id=template_entity.id, subject="Updated subject")],
    )

    snapshot = service.update_configuration(payload, principal)

    assert snapshot.provider.max_concurrent_calls == 15
    assert len(audit_logger.records) == 1
    assert audit_logger.records[0].changes["provider"]["max_concurrent_calls"]["new"] == 15