from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Iterable, Iterator, List
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.reporting.exceptions import CampaignNotFoundError, CsvExportError
from app.reporting.value_objects import (
    CampaignStats,
    ContactListFilters,
    ContactSummary,
    PaginatedContacts,
)

try:
    from app.infra.db import models as db_models
except ImportError as exc:  # pragma: no cover - infrastructure module must exist
    raise RuntimeError("app.infra.db.models must be importable for reporting service") from exc


CONTACT_STATE_COMPLETED = "completed"
CONTACT_STATE_REFUSED = "refused"
CONTACT_STATE_NOT_REACHED = "not_reached"
CONTACT_STATE_IN_PROGRESS = "in_progress"
CONTACT_STATE_PENDING = "pending"


class ReportingService:
    """Provides campaign statistics, contact listings, and CSV exports."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_campaign_stats(self, campaign_id: UUID) -> CampaignStats:
        if not self._campaign_exists(campaign_id):
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found.")

        stmt = (
            sa.select(db_models.Contact.state, sa.func.count(db_models.Contact.id))
            .where(db_models.Contact.campaign_id == campaign_id)
            .group_by(db_models.Contact.state)
        )
        counts = {state: count for state, count in self._session.execute(stmt)}
        total = sum(counts.values())

        completed = counts.get(CONTACT_STATE_COMPLETED, 0)
        refused = counts.get(CONTACT_STATE_REFUSED, 0)
        not_reached = counts.get(CONTACT_STATE_NOT_REACHED, 0)
        in_progress = counts.get(CONTACT_STATE_IN_PROGRESS, 0)
        pending = counts.get(CONTACT_STATE_PENDING, 0)

        def _pct(part: int) -> float:
            return round(part / total, 4) if total else 0.0

        return CampaignStats(
            campaign_id=campaign_id,
            total_contacts=total,
            completed_contacts=completed,
            refused_contacts=refused,
            not_reached_contacts=not_reached,
            in_progress_contacts=in_progress,
            pending_contacts=pending,
            completion_rate=_pct(completed),
            refusal_rate=_pct(refused),
            not_reached_rate=_pct(not_reached),
            updated_at=datetime.utcnow(),
        )

    def list_contacts(
        self,
        campaign_id: UUID,
        filters: ContactListFilters,
    ) -> PaginatedContacts:
        if not self._campaign_exists(campaign_id):
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found.")

        criteria = [db_models.Contact.campaign_id == campaign_id]
        if filters.state:
            criteria.append(db_models.Contact.state == filters.state)
        if filters.last_outcome:
            criteria.append(db_models.Contact.last_outcome == filters.last_outcome)

        base_query = sa.select(db_models.Contact).where(*criteria)

        total = self._session.scalar(
            sa.select(sa.func.count()).select_from(base_query.subquery())
        )

        order_clause = (
            db_models.Contact.last_attempt_at.desc()
            if filters.sort_desc
            else db_models.Contact.last_attempt_at.asc()
        ).nullslast()

        stmt = (
            base_query.order_by(order_clause, db_models.Contact.id)
            .offset((filters.page - 1) * filters.page_size)
            .limit(filters.page_size)
        )

        contacts = [
            ContactSummary(
                contact_id=row.Contact.id,
                external_contact_id=row.Contact.external_contact_id,
                phone_number=row.Contact.phone_number,
                email=row.Contact.email,
                state=row.Contact.state,
                attempts_count=row.Contact.attempts_count,
                last_outcome=row.Contact.last_outcome,
                last_attempt_at=row.Contact.last_attempt_at,
                updated_at=row.Contact.updated_at,
            )
            for row in self._session.execute(stmt)
        ]

        return PaginatedContacts(
            items=contacts,
            total=int(total or 0),
            page=filters.page,
            page_size=filters.page_size,
        )

    def iter_contacts_csv(self, campaign_id: UUID) -> Iterator[str]:
        if not self._campaign_exists(campaign_id):
            raise CampaignNotFoundError(f"Campaign {campaign_id} not found.")

        stmt = (
            sa.select(
                db_models.Contact.campaign_id,
                db_models.Contact.id,
                db_models.Contact.external_contact_id,
                db_models.Contact.phone_number,
                db_models.Contact.state,
                db_models.Contact.attempts_count,
                db_models.Contact.last_outcome,
                db_models.Contact.last_attempt_at,
                db_models.SurveyResponse.q1_answer,
                db_models.SurveyResponse.q2_answer,
                db_models.SurveyResponse.q3_answer,
            )
            .where(db_models.Contact.campaign_id == campaign_id)
            .outerjoin(
                db_models.SurveyResponse,
                db_models.SurveyResponse.contact_id == db_models.Contact.id,
            )
            .order_by(db_models.Contact.id)
        )

        header = [
            "campaign_id",
            "contact_id",
            "external_contact_id",
            "phone_number",
            "outcome",
            "attempt_count",
            "last_attempt_at",
            "q1_answer",
            "q2_answer",
            "q3_answer",
        ]

        try:
            yield from self._stream_csv(stmt, header)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise CsvExportError("Failed generating CSV export") from exc

    def _stream_csv(
        self,
        stmt: sa.Select,
        header: List[str],
    ) -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow(header)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        for row in self._session.execute(stmt):
            writer.writerow(
                [
                    row.campaign_id,
                    row.id,
                    row.external_contact_id or "",
                    row.phone_number,
                    row.last_outcome or row.state,
                    row.attempts_count,
                    row.last_attempt_at.isoformat() if row.last_attempt_at else "",
                    row.q1_answer or "",
                    row.q2_answer or "",
                    row.q3_answer or "",
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    def _campaign_exists(self, campaign_id: UUID) -> bool:
        stmt = sa.select(sa.literal(True)).select_from(db_models.Campaign).where(
            db_models.Campaign.id == campaign_id
        )
        return bool(self._session.execute(stmt).scalar())