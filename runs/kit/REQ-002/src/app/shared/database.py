from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import AppSettings, get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: Optional[sessionmaker] = None
_LOCK = threading.Lock()


def _create_engine(settings: AppSettings):
    connect_args = {}
    pool = None
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if settings.database_url.endswith(":memory:") or settings.database_url.endswith(
            "=memory:"
        ):
            pool = StaticPool
    engine = create_engine(
        settings.database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
        poolclass=pool,
    )
    return engine


def init_engine(settings: Optional[AppSettings] = None) -> None:
    global _engine, _SessionLocal
    settings = settings or get_settings()
    if _engine:
        return
    with _LOCK:
        if _engine:
            return
        _engine = _create_engine(settings)
        _SessionLocal = sessionmaker(bind=_engine, class_=Session, expire_on_commit=False)
        Base.metadata.create_all(bind=_engine)


def get_session(settings: AppSettings = None) -> Generator[Session, None, None]:
    if _SessionLocal is None:
        init_engine(settings)
    session = _SessionLocal()  # type: ignore[misc]
    try:
        yield session
    finally:
        session.close()


def session_factory() -> sessionmaker:
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal  # type: ignore[return-value]