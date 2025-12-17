from __future__ import annotations

import uuid

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Compatibility Base.

    Several earlier kits import:
        from app.auth.models import Base
    but app.auth.models didn't exist as a module in the current namespace.
    This file provides it without modifying promoted kits.
    """


class User(Base):
    """
    Minimal User model for tests/compat.

    Kept intentionally small; it exists mainly so tests/fixtures can construct users
    and for any imports expecting User to exist in app.auth.models.
    """
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    oidc_sub = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
