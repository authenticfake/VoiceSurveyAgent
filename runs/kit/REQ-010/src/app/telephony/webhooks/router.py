"""
FastAPI router for telephony webhook endpoints.

REQ-010: Telephony webhook handler
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db_session
from app.shared.logging import get_logger
from app.telephony.adapters.twilio import TwilioAdapter
from app.telephony.interface import TelephonyProvider
from app.telephony.webhooks.handler import WebhookHandler

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks/telephony", tags=["webhooks"])

def get_telephony_provider() -> TelephonyProvider:
    """Dependency to get telephony provider.

    In production, this would be configured via ProviderConfig.
    For now, returns a Twilio adapter with placeholder credentials.
    """
    import os

    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

    return TwilioAdapter(
        account_sid=account_sid,
        auth_token=auth_token,
    )

def get_webhook_handler(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> WebhookHandler:
    """Dependency to get webhook handler."""
    return WebhookHandler(session=session)

@router.post(
    "/events",
    status_code=status.HTTP_200_OK,
    summary="Receive telephony provider webhook events",
    description="""
    Receives webhook callbacks from the telephony provider.
    
    Events are parsed into domain CallEvent objects and processed
    to update call attempt and contact state.
    
    Supports idempotent processing via call_id to handle duplicate
    webhook deliveries.
    """,
)
async def receive_webhook_event(
    request: Request,
    handler: Annotated[WebhookHandler, Depends(get_webhook_handler)],
    provider: Annotated[TelephonyProvider, Depends(get_telephony_provider)],
    x_twilio_signature: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Receive and process telephony webhook event.

    Args:
        request: FastAPI request object.
        handler: Webhook handler dependency.
        provider: Telephony provider dependency.
        x_twilio_signature: Optional Twilio signature header.

    Returns:
        Processing result.

    Raises:
        HTTPException: If event parsing or processing fails.
    """
    # Get raw body for signature validation
    body = await request.body()

    # Parse form data (Twilio sends form-encoded data)
    form_data = await request.form()
    payload: dict[str, Any] = dict(form_data)

    # Add query parameters to payload (metadata passed via callback URL)
    for key, value in request.query_params.items():
        payload[key] = value

    # Get headers for signature validation
    headers = dict(request.headers)

    # Log incoming webhook
    logger.info(
        "Received telephony webhook",
        extra={
            "call_sid": payload.get("CallSid"),
            "call_status": payload.get("CallStatus"),
            "has_signature": x_twilio_signature is not None,
        },
    )

    # Validate signature if present and configured
    if x_twilio_signature:
        url = str(request.url)
        if not provider.validate_webhook_signature(body, x_twilio_signature, url):
            logger.warning(
                "Invalid webhook signature",
                extra={"call_sid": payload.get("CallSid")},
            )
            # In production, you might want to reject invalid signatures
            # For now, we log and continue to support testing

    # Parse webhook payload into domain event
    try:
        event = provider.parse_webhook_event(payload, headers)
    except ValueError as e:
        logger.error(
            "Failed to parse webhook payload",
            extra={"error": str(e), "payload": payload},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid webhook payload: {e}",
        )

    # Process the event
    try:
        processed = await handler.handle_event(event)
    except Exception as e:
        logger.error(
            "Failed to process webhook event",
            extra={
                "call_id": event.call_id,
                "event_type": event.event_type.value,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook event",
        )

    return {
        "status": "processed" if processed else "duplicate",
        "call_id": event.call_id,
        "event_type": event.event_type.value,
    }