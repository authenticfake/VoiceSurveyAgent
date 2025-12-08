from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.calling.dialogue.dependencies import get_telephony_event_processor
from app.calling.dialogue.exceptions import CallAttemptNotFoundError, DialogueProcessingError
from app.calling.dialogue.models import TelephonyEventPayload
from app.calling.dialogue.processor import TelephonyEventProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/telephony", tags=["telephony-webhooks"])


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def ingest_telephony_event(
    payload: TelephonyEventPayload,
    processor: TelephonyEventProcessor = Depends(get_telephony_event_processor),
) -> dict[str, str]:
    try:
        processor.process(payload)
    except CallAttemptNotFoundError:
        logger.warning(
            "Ignored telephony event for unknown call attempt",
            extra={"call_id": payload.call_id, "provider_call_id": payload.provider_call_id},
        )
    except DialogueProcessingError as exc:
        logger.exception("Failed to process telephony event.")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "accepted"}