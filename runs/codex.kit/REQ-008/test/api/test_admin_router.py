from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.admin.domain.models import (
    AdminConfigurationUpdateRequest,
    AdminConfigurationView,
    EmailProviderSettingsModel,
    EmailTemplateModel,
    ProviderConfigModel,
    RetentionSettingsModel,
)
from app.api.http.admin.router import admin_required, router
from app.admin.services.config_service import AdminConfigService


class FakeService(AdminConfigService):
    def __init__(self, response: AdminConfigurationView):
        self._response = response
        self.update_calls: list[AdminConfigurationUpdateRequest] = []

    def get_configuration(self) -> AdminConfigurationView:
        return self._response

    def update_configuration(self, payload, principal):
        self.update_calls.append(payload)
        return self._response


@pytest.fixture()
def fastapi_app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture()
def sample_snapshot():
    provider = ProviderConfigModel(
        id=uuid4(),
        provider_type="telephony_api",
        provider_name="twilio",
        outbound_number="+12065550100",
        max_concurrent_calls=10,
        llm_provider="openai",
        llm_model="gpt-4.1-mini",
        recording_retention_days=180,
        transcript_retention_days=180,
    )
    template = EmailTemplateModel(
        id=uuid4(),
        name="Completed EN",
        type="completed",
        locale="en",
        subject="Subject",
        body_html="<p>Body</p>",
        body_text=None,
    )
    return AdminConfigurationView(
        provider=provider,
        retention=RetentionSettingsModel(
            recording_retention_days=provider.recording_retention_days,
            transcript_retention_days=provider.transcript_retention_days,
        ),
        email_provider=EmailProviderSettingsModel(provider="ses"),
        email_templates=[template],
    )


@pytest.mark.asyncio
async def test_get_admin_configuration_returns_snapshot(fastapi_app, sample_snapshot):
    fake_service = FakeService(sample_snapshot)
    fastapi_app.dependency_overrides[admin_required] = lambda: SimpleNamespace(
        user_id=uuid4(), email="admin@example.com", role=SimpleNamespace(value="admin")
    )
    fastapi_app.dependency_overrides[
        Depends
    ] = lambda dependency: fake_service if dependency == AdminConfigService else dependency
    fastapi_app.dependency_overrides.update({})

    fastapi_app.dependency_overrides[admin_required] = lambda: SimpleNamespace(
        user_id=uuid4(), email="admin@example.com", role=SimpleNamespace(value="admin")
    )
    fastapi_app.dependency_overrides[
        AdminConfigService
    ] = lambda: fake_service  # type: ignore[assignment]
    fastapi_app.dependency_overrides[admin_required] = lambda: SimpleNamespace(
        user_id=uuid4(), email="admin@example.com", role=SimpleNamespace(value="admin")
    )
    fastapi_app.dependency_overrides[AdminConfigService] = lambda: fake_service  # type: ignore[assignment]

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/admin/config")
    assert response.status_code == 200
    assert response.json()["provider"]["provider_name"] == "twilio"


@pytest.mark.asyncio
async def test_put_admin_configuration_invokes_service(fastapi_app, sample_snapshot):
    fake_service = FakeService(sample_snapshot)
    fastapi_app.dependency_overrides[admin_required] = lambda: SimpleNamespace(
        user_id=uuid4(), email="admin@example.com", role=SimpleNamespace(value="admin")
    )
    fastapi_app.dependency_overrides[AdminConfigService] = lambda: fake_service  # type: ignore[assignment]

    payload = {
        "provider": {
            "provider_type": "telephony_api",
            "provider_name": "twilio",
            "outbound_number": "+123",
            "max_concurrent_calls": 5,
            "llm_provider": "openai",
            "llm_model": "gpt-4.1-mini",
        },
        "retention": {"recording_retention_days": 200, "transcript_retention_days": 200},
        "email_templates": [],
    }

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put("/api/admin/config", json=payload)

    assert response.status_code == 200
    assert len(fake_service.update_calls) == 1