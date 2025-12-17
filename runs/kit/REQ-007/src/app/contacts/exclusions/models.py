"""
SQLAlchemy models for exclusion list entries.

REQ-007: Exclusion list management
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.models import Base

# Backward-compat export (alcuni test/import potrebbero referenziarlo)
ExclusionBase = Base


class ExclusionSource(str, Enum):
    """Source of exclusion entry."""
    IMPORT = "import"
    API = "api"
    MANUAL = "manual"


class ExclusionListEntry(Base):
    """Exclusion list entry model matching the database schema from REQ-001."""

    __tablename__ = "exclusion_list_entries"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    phone_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # IMPORTANT:
    # - values_callable forza il DB a salvare i *value* ("api", "import", ...)
    #   invece dei *name* ("API", "IMPORT", ...)
    source: Mapped[ExclusionSource] = mapped_column(
        SQLEnum(
            ExclusionSource,
            name="exclusion_source",
            create_type=False,
            native_enum=True,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=ExclusionSource.API,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<ExclusionListEntry(id={self.id}, "
            f"phone={self.phone_number}, source={self.source})>"
        )
