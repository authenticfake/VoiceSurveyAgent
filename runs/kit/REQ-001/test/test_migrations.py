"""Tests for database migrations."""
import os
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from alembic.config import Config
from alembic import command


def get_test_database_url() -> str:
    """Get test database URL from environment."""
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "voicesurveyagent_test")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


@pytest.fixture(scope="module")
def alembic_config() -> Config:
    """Create Alembic configuration for tests."""
    config = Config()
    config.set_main_option("script_location", "runs/kit/REQ-001/src/data/migrations/migrations")
    config.set_main_option("sqlalchemy.url", get_test_database_url())
    return config


@pytest.fixture(scope="module")
def engine() -> Engine:
    """Create database engine for tests."""
    return create_engine(get_test_database_url())


@pytest.fixture(scope="module", autouse=True)
def setup_database(engine: Engine, alembic_config: Config):
    """Set up test database with migrations."""
    # Drop all existing tables and types
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    
    # Run all migrations
    command.upgrade(alembic_config, "head")
    
    yield
    
    # Cleanup after tests
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()


class TestMigrations:
    """Test suite for database migrations."""
    
    def test_all_tables_created(self, engine: Engine):
        """Verify all expected tables are created."""
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            "users",
            "email_templates",
            "campaigns",
            "contacts",
            "exclusion_list_entries",
            "call_attempts",
            "survey_responses",
            "events",
            "email_notifications",
            "provider_config",
            "transcript_snippets",
            "alembic_version",
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
    
    def test_enum_types_created(self, engine: Engine):
        """Verify all enum types are created."""
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT typname FROM pg_type 
                WHERE typtype = 'e' 
                ORDER BY typname
            """))
            enum_names = [row[0] for row in result]
        
        expected_enums = [
            "call_outcome",
            "campaign_status",
            "contact_language",
            "contact_state",
            "email_status",
            "email_template_type",
            "event_type",
            "exclusion_source",
            "language_code",
            "llm_provider",
            "provider_type",
            "question_type",
            "user_role",
        ]
        
        for enum_name in expected_enums:
            assert enum_name in enum_names, f"Enum {enum_name} not found"
    
    def test_users_table_structure(self, engine: Engine):
        """Verify users table has correct columns."""
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("users")}
        
        assert "id" in columns
        assert "oidc_sub" in columns
        assert "email" in columns
        assert "name" in columns
        assert "role" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
        
        # Check UUID type for id
        assert "UUID" in str(columns["id"]["type"]).upper()
    
    def test_campaigns_table_structure(self, engine: Engine):
        """Verify campaigns table has correct columns and foreign keys."""
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("campaigns")}
        
        expected_columns = [
            "id", "name", "description", "status", "language",
            "intro_script", "question_1_text", "question_1_type",
            "question_2_text", "question_2_type", "question_3_text",
            "question_3_type", "max_attempts", "retry_interval_minutes",
            "allowed_call_start_local", "allowed_call_end_local",
            "email_completed_template_id", "email_refused_template_id",
            "email_not_reached_template_id", "created_by_user_id",
            "created_at", "updated_at",
        ]
        
        for col in expected_columns:
            assert col in columns, f"Column {col} not found in campaigns"
        
        # Check foreign keys
        fks = inspector.get_foreign_keys("campaigns")
        fk_columns = [fk["constrained_columns"][0] for fk in fks]
        
        assert "email_completed_template_id" in fk_columns
        assert "email_refused_template_id" in fk_columns
        assert "email_not_reached_template_id" in fk_columns
        assert "created_by_user_id" in fk_columns
    
    def test_contacts_table_indexes(self, engine: Engine):
        """Verify contacts table has required indexes."""
        inspector = inspect(engine)
        indexes = {idx["name"]: idx for idx in inspector.get_indexes("contacts")}
        
        # Check for scheduler lookup composite index
        assert "ix_contacts_scheduler_lookup" in indexes
        scheduler_idx = indexes["ix_contacts_scheduler_lookup"]
        assert "campaign_id" in scheduler_idx["column_names"]
        assert "state" in scheduler_idx["column_names"]
        assert "attempts_count" in scheduler_idx["column_names"]
        assert "do_not_call" in scheduler_idx["column_names"]
    
    def test_call_attempts_table_structure(self, engine: Engine):
        """Verify call_attempts table has correct structure."""
        inspector = inspect(engine)
        columns = {col["name"]: col for col in inspector.get_columns("call_attempts")}
        
        assert "call_id" in columns
        assert "provider_call_id" in columns
        assert "metadata" in columns
        
        # Check unique constraint on call_id
        unique_constraints = inspector.get_unique_constraints("call_attempts")
        call_id_unique = any(
            "call_id" in uc.get("column_names", [])
            for uc in unique_constraints
        )
        assert call_id_unique or any(
            idx.get("unique") and "call_id" in idx.get("column_names", [])
            for idx in inspector.get_indexes("call_attempts")
        )
    
    def test_survey_responses_unique_constraint(self, engine: Engine):
        """Verify survey_responses has unique constraint on contact_id + campaign_id."""
        inspector = inspect(engine)
        unique_constraints = inspector.get_unique_constraints("survey_responses")
        
        found = False
        for uc in unique_constraints:
            cols = uc.get("column_names", [])
            if "contact_id" in cols and "campaign_id" in cols:
                found = True
                break
        
        assert found, "Unique constraint on contact_id + campaign_id not found"
    
    def test_exclusion_list_entries_unique_phone(self, engine: Engine):
        """Verify exclusion_list_entries has unique phone_number."""
        inspector = inspect(engine)
        unique_constraints = inspector.get_unique_constraints("exclusion_list_entries")
        indexes = inspector.get_indexes("exclusion_list_entries")
        
        phone_unique = any(
            "phone_number" in uc.get("column_names", [])
            for uc in unique_constraints
        ) or any(
            idx.get("unique") and "phone_number" in idx.get("column_names", [])
            for idx in indexes
        )
        
        assert phone_unique, "phone_number should be unique"


class TestMigrationIdempotency:
    """Test that migrations are idempotent."""
    
    def test_migrations_can_run_multiple_times(self, alembic_config: Config, engine: Engine):
        """Verify migrations can be run multiple times without error."""
        # Downgrade to base
        command.downgrade(alembic_config, "base")
        
        # Upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "campaigns" in tables
        
        # Downgrade and upgrade again
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
        
        # Verify tables still exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "campaigns" in tables


class TestMigrationRollback:
    """Test migration rollback functionality."""
    
    def test_each_migration_has_downgrade(self, alembic_config: Config, engine: Engine):
        """Verify each migration can be rolled back."""
        # Start from head
        command.upgrade(alembic_config, "head")
        
        # Get all revisions
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_config)
        revisions = list(script.walk_revisions())
        
        # Downgrade one by one
        for rev in revisions:
            if rev.down_revision is not None:
                command.downgrade(alembic_config, rev.down_revision)
        
        # Downgrade to base
        command.downgrade(alembic_config, "base")
        
        # Verify all tables are dropped
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Only alembic_version should remain (or be empty)
        assert len([t for t in tables if t != "alembic_version"]) == 0
        
        # Upgrade back to head
        command.upgrade(alembic_config, "head")