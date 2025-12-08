from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.events.bus.publisher import DbSurveyEventPublisher
from app.infra.db.session import get_db_session

from .processor import TelephonyEventProcessor


def get_telephony_event_processor(
    session: Session = Depends(get_db_session),
) -> TelephonyEventProcessor:
    publisher = DbSurveyEventPublisher(session)
    return TelephonyEventProcessor(session=session, event_publisher=publisher)