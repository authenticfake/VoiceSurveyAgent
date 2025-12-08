from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from app.contacts.domain.enums import ContactLanguage, ContactState
from app.infra.db.base import Base


class ContactModel(Base):
    __tablename__ = "contacts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(PGUUID(as_uuid=True), nullable=False)
    external_contact_id = Column(String(255), nullable=True)
    phone_number = Column(String(32), nullable=False)
    email = Column(String(320), nullable=True)
    preferred_language = Column(Enum(ContactLanguage, name="contact_language_enum"), nullable=False)
    has_prior_consent = Column(Integer, nullable=False, default=0)
    do_not_call = Column(Integer, nullable=False, default=0)
    state = Column(Enum(ContactState, name="contact_state_enum"), nullable=False)
    attempts_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_outcome = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("campaign_id", "phone_number", name="uq_contacts_campaign_phone"),
        Index("ix_contacts_campaign_state", "campaign_id", "state"),
        Index("ix_contacts_phone", "phone_number"),
    )


class ExclusionListEntryModel(Base):
    __tablename__ = "exclusion_list_entries"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(32), nullable=False, unique=True)
    reason = Column(Text, nullable=True)
    source = Column(String(32), nullable=False, default="imported")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)