import pytest
SKIP_INTEGRATION = True
SKIP_REASON = "Integration tests disabled by default for REQ-014 (logic tests are sync/in-memory)."

@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
class TestPersistenceIntegration:
    """Integration tests for persistence layer."""

    def test_full_persistence_flow_smoke(self) -> None:
        """Smoke: ensure the service can be imported/instantiated.

        Kept sync-only to avoid pytest-asyncio dependency in the default suite.
        """
        from app.dialogue.persistence import SurveyPersistenceService

        service = SurveyPersistenceService()
        assert service is not None
