"""Engine and session helpers for database access."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine_from_url(database_url: str, *, echo: bool | None = None) -> Engine:
    """Create a SQLAlchemy engine configured for Postgres."""
    return create_engine(
        database_url,
        pool_pre_ping=True,
        echo=bool(echo),
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a configured session factory."""
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - re-raised upstream
        session.rollback()
        raise
    finally:
        session.close()


def default_engine_from_env(env_var: str = "DATABASE_URL", *, echo: bool | None = None) -> Engine:
    """Convenience helper that reads the DB URL from an environment variable."""
    database_url = os.getenv(env_var)
    if not database_url:  # pragma: no cover - guard rail
        raise RuntimeError(f"{env_var} is not set")
    return create_engine_from_url(database_url, echo=echo)