from fastapi.testclient import TestClient

from app.main import app
from app.telephony.webhooks import router


class FakeProvider:
    def parse_webhook_event(self, payload):
        from app.telephony.interface import WebhookEvent, WebhookEventType, CallStatus
        from datetime import datetime
        return WebhookEvent(
            event_type=WebhookEventType.CALL_COMPLETED,
            provider="fake",
            provider_call_id="p1",
            call_id="call-x",
            campaign_id=None,
            contact_id=None,
            status=CallStatus.COMPLETED,
            timestamp=datetime.utcnow(),
        )


class FakeHandler:
    def __init__(self):
        self.called = False

    def handle(self, event):
        self.called = True
        return True


def test_webhook_router_smoke_sync(monkeypatch):
    fake_handler = FakeHandler()

    monkeypatch.setattr(router, "get_telephony_provider", lambda: FakeProvider())
    monkeypatch.setattr(router, "get_webhook_handler", lambda: fake_handler)

    client = TestClient(app)

    resp = client.post(
        "/webhooks/telephony/events",
        data={"CallSid": "123"},
    )

    assert resp.status_code in (200, 204)
    assert fake_handler.called is True
