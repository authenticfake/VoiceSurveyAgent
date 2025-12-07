from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.campaigns.domain.enums import CampaignLanguage, CampaignStatus, QuestionAnswerType
from app.campaigns.domain.errors import CampaignNotFoundError
from app.campaigns.domain.models import (
    CallWindow,
    CampaignQuestion,
    CampaignRecord,
    EmailTemplateConfig,
    RetryPolicy,
)
from app.campaigns.persistence.models import CampaignModel
from app.campaigns.services.interfaces import CampaignFilters, CampaignRepository, PaginationParams


class SqlAlchemyCampaignRepository(CampaignRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, data: Mapping[str, object], created_by: UUID) -> CampaignRecord:
        model = CampaignModel(**data, created_by_user_id=created_by)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def update(self, campaign_id: UUID, data: Mapping[str, object]) -> CampaignRecord:
        model = self.session.get(CampaignModel, campaign_id)
        if model is None:
            raise CampaignNotFoundError("Campaign was not found.")
        for key, value in data.items():
            setattr(model, key, value)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def update_status(self, campaign_id: UUID, status: str) -> CampaignRecord:
        return self.update(campaign_id, {"status": status})

    def get(self, campaign_id: UUID) -> CampaignRecord | None:
        model = self.session.get(CampaignModel, campaign_id)
        return self._to_domain(model) if model else None

    def list(
        self,
        filters: CampaignFilters,
        pagination: PaginationParams,
    ) -> tuple[Sequence[CampaignRecord], int]:
        query = self.session.query(CampaignModel)
        if filters.status:
            query = query.filter(CampaignModel.status == filters.status)
        if filters.created_from:
            query = query.filter(CampaignModel.created_at >= filters.created_from)
        if filters.created_to:
            query = query.filter(CampaignModel.created_at <= filters.created_to)

        total_items = query.count()
        items = (
            query.order_by(CampaignModel.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
            .all()
        )
        return [self._to_domain(model) for model in items], total_items

    def _to_domain(self, model: CampaignModel) -> CampaignRecord:
        questions = [
            CampaignQuestion(
                position=1,
                text=model.question_1_text,
                answer_type=QuestionAnswerType(model.question_1_type),
            ),
            CampaignQuestion(
                position=2,
                text=model.question_2_text,
                answer_type=QuestionAnswerType(model.question_2_type),
            ),
            CampaignQuestion(
                position=3,
                text=model.question_3_text,
                answer_type=QuestionAnswerType(model.question_3_type),
            ),
        ]
        retry_policy = RetryPolicy(
            max_attempts=model.max_attempts,
            retry_interval_minutes=model.retry_interval_minutes,
        )
        call_window = CallWindow(
            start_local=model.allowed_call_start_local,
            end_local=model.allowed_call_end_local,
        )
        email_templates = EmailTemplateConfig(
            completed_template_id=model.email_completed_template_id,
            refused_template_id=model.email_refused_template_id,
            not_reached_template_id=model.email_not_reached_template_id,
        )
        return CampaignRecord(
            id=model.id,
            name=model.name,
            description=model.description,
            status=CampaignStatus(model.status),
            language=CampaignLanguage(model.language),
            intro_script=model.intro_script,
            questions=questions,
            retry_policy=retry_policy,
            call_window=call_window,
            email_templates=email_templates,
            created_by_user_id=model.created_by_user_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )