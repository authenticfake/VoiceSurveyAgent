from __future__ import annotations

import io
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.http.contacts.router import router
from app.auth.domain.models import Role, UserPrincipal
from app.contacts.persistence.repository import (
    ContactFilters,
    Pagination,
    SqlAlchemyContactRepository,
    SqlAlchemyExclusionListRepository,
)
from app.contacts.services.dependencies import get_contact_service
from app.contacts.services.service import ContactService
from app.infra.db.base import Base
from app.infra.db.session import SessionLocal


@pytest_asyncio.fixture
async def client(tmp_path_factory) -> AsyncClient:
    Base.metadata.drop_all(bind=SessionLocal.get_bind(), checkfirst=True)
    Base.metadata.create_all(bind=SessionLocal.get_bind(), checkfirst=True)
    app = FastAPI()
    app.include_router(router)

    def override_current_user():
        return UserPrincipal(id=uuid4(), email="user@example.com", role=Role.campaign_manager)

    def override_service():
        session = SessionLocal()
        repository = SqlAlchemyContactRepository(session)
        exclusion_repository = SqlAlchemyExclusionListRepository(session)
        importer = ContactCSVImporter(repository=repository, exclusion_repository=exclusion_repository)
        return ContactService(repository=repository, importer=importer)

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_contact_service] = override_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.mark.asyncio
async def test_upload_contacts_endpoint(client: AsyncClient):
    campaign_id = uuid4()
    csv_content = (
        "phone_number,has_prior_consent,do_not_call\n"
        "+15550000001,true,false\n"
        "+15550000002,false,true\n"
    )
    response = await client.post(
        f"/api/campaigns/{campaign_id}/contacts/upload",
        files={"file": ("contacts.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted_rows"] == 2
    assert body["rejected_rows"] == 0


@pytest.mark.asyncio
async def test_list_contacts_endpoint(client: AsyncClient):
    campaign_id = uuid4()
    csv_content = (
        "phone_number,has_prior_consent,do_not_call\n"
        "+15550000003,true,false\n"
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/contacts/upload",
        files={"file": ("contacts.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
    )

    response = await client.get(f"/api/campaigns/{campaign_id}/contacts?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["phone_number"].endswith("000003")