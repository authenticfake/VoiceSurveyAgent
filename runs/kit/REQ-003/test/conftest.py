from __future__ import annotations

import asyncio
from typing import AsyncIterator, Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.http.contacts.router import router as contacts_router
from app.auth.domain.models import Role, UserPrincipal
from app.contacts.persistence.models import ContactModel, ExclusionListEntryModel
from app.contacts.services.dependencies import get_contact_service
from app.infra.db.base import Base


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def engine():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(engine) -> Iterator[Session]:
    SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def campaign_id() -> str:
    return str(uuid4())


@pytest.fixture
def fastapi_app(db_session: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(contacts_router)

    def get_test_session():
        yield db_session

    from app.infra.db import session as session_module

    session_module.SessionLocal = sessionmaker(bind=db_session.get_bind(), class_=Session, expire_on_commit=False)

    def override_current_user():
        return UserPrincipal(id=uuid4(), email="user@example.com", role=Role.campaign_manager)

    app.dependency_overrides[get_contact_service] = lambda: get_contact_service()
    app.dependency_overrides[override_current_user] = override_current_user
    return app