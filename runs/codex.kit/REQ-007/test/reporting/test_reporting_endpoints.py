from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
from typing import Callable
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import Session, sessionmaker

from app.api.http.reporting import router as reporting_router
from app.api.http.reporting.router import (
    get_db_session_dependency,
    manager_role_guard,
    viewer_role_guard,
)
from app.auth.dependencies import get_current_user
from app.infra.db import models as db_models


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    db_models.Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def fastapi_app(db_session: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(reporting_router.router)

    def _session_override() -> Session:
        return db_session

    app.dependency_overrides[get_db_session_dependency] = _session_override
    app.dependency_overrides[get_current_user] = lambda: object()
    app.dependency_overrides[viewer_role_guard] = lambda: None
    app.dependency_overrides[manager_role_guard] = lambda: None
    yield app
    app.dependency_overrides.clear()


async def _async_client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


def _persist_campaign(session: Session) -> UUID:
    campaign_id = uuid4()
    stmt = insert(db_models.Campaign).values(
        id=campaign_id,
        name="Test Campaign",
        description="Desc",
        status="running",
        language="en",
        intro_script="Intro",
        question_1_text="Q1",
        question_1_type="free_text",
        question_2_text="Q2",
        question_2_type="free_text",
        question_3_text="Q3",
        question_3_type="free_text",
        max_attempts=3,
        retry_interval_minutes=10,
        allowed_call_start_local=time(hour=9),
        allowed_call_end_local=time(hour=20),
    )
    session.execute(stmt)
    session.commit()
    return campaign_id


def _persist_contact(
    session: Session,
    *,
    campaign_id: UUID,
    contact_id: UUID,
    state: str,
    attempts: int,
    last_outcome: str | None,
    last_attempt_at: datetime | None,
):
    stmt = insert(db_models.Contact).values(
        id=contact_id,
        campaign_id=campaign_id,
        phone_number="+15555550100",
        email="user@example.com",
        state=state,
        attempts_count=attempts,
        last_outcome=last_outcome,
        last_attempt_at=last_attempt_at,
        preferred_language="en",
        has_prior_consent=False,
        do_not_call=False,
    )
    session.execute(stmt)


def _persist_survey_response(
    session: Session,
    *,
    contact_id: UUID,
    campaign_id: UUID,
    call_attempt_id: UUID,
    q1: str,
    q2: str,
    q3: str,
):
    session.execute(
        insert(db_models.CallAttempt).values(
            id=call_attempt_id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            attempt_number=1,
            call_id=f"call-{contact_id}",
            provider_call_id=f"provider-{contact_id}",
            started_at=datetime.utcnow(),
            answered_at=datetime.utcnow(),
            ended_at=datetime.utcnow(),
            outcome="completed",
        )
    )
    session.execute(
        insert(db_models.SurveyResponse).values(
            id=uuid4(),
            contact_id=contact_id,
            campaign_id=campaign_id,
            call_attempt_id=call_attempt_id,
            q1_answer=q1,
            q2_answer=q2,
            q3_answer=q3,
        )
    )


@pytest.mark.asyncio
async def test_stats_endpoint_returns_expected_counts_and_rates(
    fastapi_app: FastAPI, db_session: Session
):
    campaign_id = _persist_campaign(db_session)
    now = datetime.utcnow()

    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=uuid4(),
        state="completed",
        attempts=2,
        last_outcome="completed",
        last_attempt_at=now,
    )
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=uuid4(),
        state="refused",
        attempts=1,
        last_outcome="refused",
        last_attempt_at=now - timedelta(minutes=10),
    )
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=uuid4(),
        state="not_reached",
        attempts=3,
        last_outcome="no_answer",
        last_attempt_at=now - timedelta(minutes=20),
    )
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=uuid4(),
        state="pending",
        attempts=0,
        last_outcome=None,
        last_attempt_at=None,
    )
    db_session.commit()

    async with await _async_client(fastapi_app) as client:
        response = await client.get(f"/api/campaigns/{campaign_id}/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_contacts"] == 4
    assert payload["completed_contacts"] == 1
    assert payload["refused_contacts"] == 1
    assert payload["not_reached_contacts"] == 1
    assert pytest.approx(payload["completion_rate"]) == 0.25
    assert pytest.approx(payload["refusal_rate"]) == 0.25
    assert pytest.approx(payload["not_reached_rate"]) == 0.25


@pytest.mark.asyncio
async def test_contacts_endpoint_supports_filters_and_pagination(
    fastapi_app: FastAPI, db_session: Session
):
    campaign_id = _persist_campaign(db_session)
    now = datetime.utcnow()

    first_contact = uuid4()
    second_contact = uuid4()
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=first_contact,
        state="completed",
        attempts=2,
        last_outcome="completed",
        last_attempt_at=now,
    )
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=second_contact,
        state="completed",
        attempts=1,
        last_outcome="completed",
        last_attempt_at=now - timedelta(minutes=5),
    )
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=uuid4(),
        state="pending",
        attempts=0,
        last_outcome=None,
        last_attempt_at=None,
    )
    db_session.commit()

    async with await _async_client(fastapi_app) as client:
        response = await client.get(
            f"/api/campaigns/{campaign_id}/contacts",
            params={"state": "completed", "page": 1, "page_size": 1, "sort": "recent"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 2
    assert len(data["items"]) == 1
    assert data["items"][0]["contact_id"] == str(first_contact)


@pytest.mark.asyncio
async def test_export_endpoint_streams_csv_with_answers(
    fastapi_app: FastAPI, db_session: Session
):
    campaign_id = _persist_campaign(db_session)
    contact_id = uuid4()
    _persist_contact(
        db_session,
        campaign_id=campaign_id,
        contact_id=contact_id,
        state="completed",
        attempts=1,
        last_outcome="completed",
        last_attempt_at=datetime.utcnow(),
    )
    _persist_survey_response(
        db_session,
        contact_id=contact_id,
        campaign_id=campaign_id,
        call_attempt_id=uuid4(),
        q1="yes",
        q2="42",
        q3="happy",
    )
    db_session.commit()

    async with await _async_client(fastapi_app) as client:
        response = await client.get(f"/api/campaigns/{campaign_id}/export")
    assert response.status_code == 200
    content = response.text.splitlines()
    assert content[0].startswith("campaign_id,contact_id")
    assert "yes" in content[1]
    assert "happy" in content[1]


@pytest.mark.asyncio
async def test_stats_404_when_campaign_missing(fastapi_app: FastAPI):
    missing_id = uuid4()
    async with await _async_client(fastapi_app) as client:
        response = await client.get(f"/api/campaigns/{missing_id}/stats")
    assert response.status_code == 404