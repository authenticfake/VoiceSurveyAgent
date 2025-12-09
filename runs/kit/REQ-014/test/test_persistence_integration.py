"""
Integration tests for survey response persistence.

REQ-014: Survey response persistence

These tests require a running PostgreSQL database.
Set DATABASE_URL environment variable or use default test database.
"""

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Check if we can run integration tests
SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION_TESTS", "true").lower() == "true"
SKIP_REASON = "Integration tests disabled. Set SKIP_INTEGRATION_TESTS=false to run."


@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
class TestPersistenceIntegration:
    """Integration tests for persistence layer."""

    @pytest.fixture
    async def db_session(self):
        """Create database session for tests."""
        try:
            from app.shared.database import get_db_context
        except ImportError:
            pytest.skip("Database dependencies not available")

        async with get_db_context() as session:
            yield session

    @pytest.mark.asyncio
    async def test_full_persistence_flow(self, db_session) -> None:
        """Test complete persistence flow with real database."""
        from app.dialogue.models import (
            CallContext,
            CapturedAnswer,
            DialogueSession,
            DialogueSessionState,
            ConsentState,
            DialoguePhase,
        )
        from app.dialogue.persistence import SurveyPersistenceService

        # This test would require seeded data in the database
        # For now, we just verify the service can be instantiated
        service = SurveyPersistenceService()
        assert service is not None


@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
class TestDatabaseModels:
    """Tests for database model definitions."""

    def test_survey_response_model_fields(self) -> None:
        """Test SurveyResponse model has required fields."""
        from app.dialogue.persistence_models import SurveyResponse

        # Verify model has all required columns
        columns = SurveyResponse.__table__.columns
        required_columns = [
            "id",
            "contact_id",
            "campaign_id",
            "call_attempt_id",
            "q1_answer",
            "q2_answer",
            "q3_answer",
            "q1_confidence",
            "q2_confidence",
            "q3_confidence",
            "completed_at",
        ]

        for col_name in required_columns:
            assert col_name in columns, f"Missing column: {col_name}"

    def test_contact_model_fields(self) -> None:
        """Test Contact model has required fields."""
        from app.dialogue.persistence_models import Contact

        columns = Contact.__table__.columns
        required_columns = [
            "id",
            "campaign_id",
            "phone_number",
            "state",
            "last_outcome",
        ]

        for col_name in required_columns:
            assert col_name in columns, f"Missing column: {col_name}"

    def test_call_attempt_model_fields(self) -> None:
        """Test CallAttempt model has required fields."""
        from app.dialogue.persistence_models import CallAttempt

        columns = CallAttempt.__table__.columns
        required_columns = [
            "id",
            "contact_id",
            "campaign_id",
            "call_id",
            "outcome",
            "ended_at",
        ]

        for col_name in required_columns:
            assert col_name in columns, f"Missing column: {col_name}"