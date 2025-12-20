from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.telephony.webhooks import router


class FakeProvider:
    def parse_webhook_event(self, payload, headers=None):
        from datetime import datetime
        from app.telephony.interface import WebhookEvent, WebhookEventType, CallStatus

        return WebhookEvent(
            event_type=WebhookEventType.CALL_COMPLETED,
            provider="fake",
            provider_call_id="p1",
            call_id="call-x",
            campaign_id=None,
            contact_id=None,
            status=CallStatus.COMPLETED,
            timestamp=datetime.utcnow(),
            raw_payload=payload,
        )

    def validate_webhook_signature(self, payload, signature, url=None):
        return True



class FakeHandler:
    def __init__(self):
        self.called = False
        self.last_event = None

    async def handle_event(self, event):
        self.called = True
        self.last_event = event
        return {"ok": True}




def test_webhook_router_smoke_sync(monkeypatch):
    fake_handler = FakeHandler()

    monkeypatch.setattr(router, "get_telephony_provider", lambda: FakeProvider())
    monkeypatch.setattr(router, "get_webhook_handler", lambda: fake_handler)

    app = FastAPI()
    app.include_router(router.router)  # <-- usa l'APIRouter del modulo

    client = TestClient(app)

    resp = client.post(
        "/webhooks/telephony/events",
        data={"CallSid": "123"},
    )

    assert resp.status_code in (200, 204)
    assert fake_handler.called is True
