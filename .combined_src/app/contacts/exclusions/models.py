"""
SQLAlchemy models for exclusion list entries.

REQ-007: Exclusion list management
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Type
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Enum as SAEnum
from enum import Enum as PyEnum
from app.auth.models import Base

# Backward-compat export (alcuni test/import potrebbero referenziarlo)
ExclusionBase = Base

def _enum_values(enum_cls: Type[PyEnum]) -> list[str]:
    return [e.value for e in enum_cls]  # type: ignore[attr-defined]

class ExclusionSource(str, Enum):
    """Source of exclusion entry."""
    IMPORT = "import"
    API = "api"
    MANUAL = "manual"

EXCLUSION_SOURCE_DB_ENUM = SAEnum(
    ExclusionSource,
    name="exclusion_source",
    create_type=False,
    values_callable=_enum_values,
    validate_strings=True,
)
class ExclusionListEntry(Base):
    """Exclusion list entry model."""

    __tablename__ = "exclusion_list_entries"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    phone_number: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        index=True,
    )

    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # IMPORTANT:
    # - create_type=False: non prova a creare l'enum nel DB (lo gestisci via migrazioni/schema)
    # - values_callable: salva i VALUE (IMPORT/API/MANUAL) e non i name/altre trasformazioni
    source: Mapped[ExclusionSource] = mapped_column(
        EXCLUSION_SOURCE_DB_ENUM,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
