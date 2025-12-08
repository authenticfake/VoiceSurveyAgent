from app.infra.db import models
from app.infra.db.base import Base


def test_expected_tables_registered():
    expected = {
        "users",
        "email_templates",
        "campaigns",
        "contacts",
        "exclusion_list_entries",
        "call_attempts",
        "survey_responses",
        "events",
        "email_notifications",
        "provider_configurations",
        "transcript_snippets",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_campaign_model_fields_cover_core_spec():
    columns = {column.name for column in models.Campaign.__table__.columns}
    required = {
        "status",
        "language",
        "intro_script",
        "question_1_text",
        "question_2_text",
        "question_3_text",
        "max_attempts",
        "retry_interval_minutes",
        "allowed_call_start_local",
        "allowed_call_end_local",
    }
    assert required.issubset(columns)


def test_enum_values_match_spec():
    assert {role.value for role in models.UserRole} == {
        "admin",
        "campaign_manager",
        "viewer",
    }
    assert {state.value for state in models.ContactState} == {
        "pending",
        "in_progress",
        "completed",
        "refused",
        "not_reached",
        "excluded",
    }
    assert {etype.value for etype in models.EventType} == {
        "survey.completed",
        "survey.refused",
        "survey.not_reached",
    }