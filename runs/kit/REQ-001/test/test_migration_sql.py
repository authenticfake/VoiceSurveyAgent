"""
Test suite for REQ-001: Database schema and migrations
Tests shape, idempotency, and round-trip of SQL migrations
"""

import os
import pytest
from typing import Generator
import psycopg
from psycopg.rows import dict_row

# Skip all tests if no database URL is provided
DATABASE_URL = os.environ.get("DATABASE_URL")
SKIP_REASON = "DATABASE_URL not set - skipping database tests"

# Check for testcontainers availability
try:
    from testcontainers.postgres import PostgresContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False

# Check if testcontainers should be disabled
DISABLE_TESTCONTAINERS = os.environ.get("DISABLE_TESTCONTAINERS", "0") == "1"

def get_sql_path(filename: str) -> str:
    """Get path to SQL file relative to test location."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, "..", "src", "storage", "sql", filename)

def get_seed_path() -> str:
    """Get path to seed SQL file."""
    test_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(test_dir, "..", "src", "storage", "seed", "seed.sql")

@pytest.fixture(scope="module")
def database_url() -> Generator[str, None, None]:
    """
    Provide a database URL for testing.
    Uses testcontainers if available and not disabled, otherwise falls back to DATABASE_URL.
    """
    if TESTCONTAINERS_AVAILABLE and not DISABLE_TESTCONTAINERS:
        with PostgresContainer("postgres:15-alpine") as postgres:
            yield postgres.get_connection_url().replace("postgresql+psycopg2://", "postgresql://")
    elif DATABASE_URL:
        yield DATABASE_URL
    else:
        pytest.skip(SKIP_REASON)

@pytest.fixture
def db_connection(database_url: str) -> Generator[psycopg.Connection, None, None]:
    """Create a database connection for testing."""
    conn = psycopg.connect(database_url, row_factory=dict_row)
    yield conn
    conn.close()

@pytest.fixture
def clean_database(db_connection: psycopg.Connection) -> Generator[psycopg.Connection, None, None]:
    """Ensure database is clean before each test."""
    # Run down migration to clean up
    down_sql_path = get_sql_path("V0001.down.sql")
    if os.path.exists(down_sql_path):
        with open(down_sql_path, "r") as f:
            down_sql = f.read()
        try:
            db_connection.execute(down_sql)
            db_connection.commit()
        except Exception:
            db_connection.rollback()
    
    yield db_connection

class TestMigrationShape:
    """Test that migrations create the expected schema shape."""

    def test_up_migration_creates_all_tables(self, clean_database: psycopg.Connection) -> None:
        """Verify all expected tables are created by up migration."""
        conn = clean_database
        
        # Run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        
        conn.execute(up_sql)
        conn.commit()
        
        # Check all expected tables exist
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
            "provider_configs",
            "transcript_snippets",
        ]
        
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """).fetchall()
        
        actual_tables = {row["table_name"] for row in result}
        
        for table in expected_tables:
            assert table in actual_tables, f"Table {table} not found in schema"

    def test_up_migration_creates_all_enum_types(self, clean_database: psycopg.Connection) -> None:
        """Verify all expected enum types are created."""
        conn = clean_database
        
        # Run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        
        conn.execute(up_sql)
        conn.commit()
        
        expected_enums = [
            "user_role",
            "campaign_status",
            "campaign_language",
            "question_type",
            "contact_state",
            "contact_language",
            "contact_outcome",
            "exclusion_source",
            "event_type",
            "email_status",
            "email_template_type",
            "provider_type",
            "llm_provider",
        ]
        
        result = conn.execute("""
            SELECT typname 
            FROM pg_type 
            WHERE typtype = 'e'
        """).fetchall()
        
        actual_enums = {row["typname"] for row in result}
        
        for enum in expected_enums:
            assert enum in actual_enums, f"Enum type {enum} not found"

    def test_uuid_primary_keys(self, clean_database: psycopg.Connection) -> None:
        """Verify UUID primary keys are used for all tables."""
        conn = clean_database
        
        # Run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        
        conn.execute(up_sql)
        conn.commit()
        
        tables_with_pk = [
            "users",
            "email_templates",
            "campaigns",
            "contacts",
            "exclusion_list_entries",
            "call_attempts",
            "survey_responses",
            "events",
            "email_notifications",
            "provider_configs",
            "transcript_snippets",
        ]
        
        for table in tables_with_pk:
            result = conn.execute("""
                SELECT c.column_name, c.data_type
                FROM information_schema.columns c
                JOIN information_schema.table_constraints tc 
                    ON c.table_name = tc.table_name 
                    AND tc.constraint_type = 'PRIMARY KEY'
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name 
                    AND c.column_name = kcu.column_name
                WHERE c.table_name = %s
            """, (table,)).fetchone()
            
            assert result is not None, f"No primary key found for table {table}"
            assert result["data_type"] == "uuid", f"Primary key for {table} is not UUID type"

    def test_foreign_key_indexes_exist(self, clean_database: psycopg.Connection) -> None:
        """Verify indexes exist on foreign key columns."""
        conn = clean_database
        
        # Run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        
        conn.execute(up_sql)
        conn.commit()
        
        # Check for indexes on key foreign key columns
        expected_indexes = [
            ("contacts", "idx_contacts_campaign_id"),
            ("call_attempts", "idx_call_attempts_contact_id"),
            ("call_attempts", "idx_call_attempts_campaign_id"),
            ("survey_responses", "idx_survey_responses_contact_id"),
            ("survey_responses", "idx_survey_responses_campaign_id"),
            ("events", "idx_events_campaign_id"),
            ("events", "idx_events_contact_id"),
            ("email_notifications", "idx_email_notifications_contact_id"),
            ("email_notifications", "idx_email_notifications_campaign_id"),
        ]
        
        for table, index_name in expected_indexes:
            result = conn.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = %s AND indexname = %s
            """, (table, index_name)).fetchone()
            
            assert result is not None, f"Index {index_name} not found on table {table}"

class TestMigrationIdempotency:
    """Test that migrations are idempotent."""

    def test_up_migration_is_idempotent(self, clean_database: psycopg.Connection) -> None:
        """Verify up migration can be run multiple times without error."""
        conn = clean_database
        
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        
        # Run migration twice
        conn.execute(up_sql)
        conn.commit()
        
        # Second run should not raise an error
        conn.execute(up_sql)
        conn.commit()
        
        # Verify tables still exist
        result = conn.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """).fetchone()
        
        assert result["count"] >= 11, "Expected at least 11 tables after idempotent migration"

    def test_down_migration_is_idempotent(self, clean_database: psycopg.Connection) -> None:
        """Verify down migration can be run multiple times without error."""
        conn = clean_database
        
        # First run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        conn.execute(up_sql)
        conn.commit()
        
        # Run down migration twice
        down_sql_path = get_sql_path("V0001.down.sql")
        with open(down_sql_path, "r") as f:
            down_sql = f.read()
        
        conn.execute(down_sql)
        conn.commit()
        
        # Second run should not raise an error
        conn.execute(down_sql)
        conn.commit()
        
        # Verify tables are gone
        result = conn.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name IN ('users', 'campaigns', 'contacts')
        """).fetchone()
        
        assert result["count"] == 0, "Tables should be dropped after down migration"

class TestMigrationRoundTrip:
    """Test up/down/up round-trip."""

    def test_round_trip_migration(self, clean_database: psycopg.Connection) -> None:
        """Verify schema is identical after up -> down -> up cycle."""
        conn = clean_database
        
        up_sql_path = get_sql_path("V0001.up.sql")
        down_sql_path = get_sql_path("V0001.down.sql")
        
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        with open(down_sql_path, "r") as f:
            down_sql = f.read()
        
        # Up
        conn.execute(up_sql)
        conn.commit()
        
        # Get initial table count
        result = conn.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """).fetchone()
        initial_count = result["count"]
        
        # Down
        conn.execute(down_sql)
        conn.commit()
        
        # Up again
        conn.execute(up_sql)
        conn.commit()
        
        # Get final table count
        result = conn.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """).fetchone()
        final_count = result["count"]
        
        assert initial_count == final_count, "Table count should be same after round-trip"

class TestSeedData:
    """Test seed data application."""

    def test_seed_data_applies_successfully(self, clean_database: psycopg.Connection) -> None:
        """Verify seed data can be applied after migration."""
        conn = clean_database
        
        # Run up migration first
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        conn.execute(up_sql)
        conn.commit()
        
        # Run seed
        seed_path = get_seed_path()
        with open(seed_path, "r") as f:
            seed_sql = f.read()
        conn.execute(seed_sql)
        conn.commit()
        
        # Verify seed data exists
        result = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        assert result["count"] >= 3, "Expected at least 3 seeded users"
        
        result = conn.execute("SELECT COUNT(*) as count FROM email_templates").fetchone()
        assert result["count"] >= 6, "Expected at least 6 seeded email templates"
        
        result = conn.execute("SELECT COUNT(*) as count FROM campaigns").fetchone()
        assert result["count"] >= 1, "Expected at least 1 seeded campaign"

    def test_seed_data_is_idempotent(self, clean_database: psycopg.Connection) -> None:
        """Verify seed data can be applied multiple times."""
        conn = clean_database
        
        # Run up migration first
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        conn.execute(up_sql)
        conn.commit()
        
        # Run seed twice
        seed_path = get_seed_path()
        with open(seed_path, "r") as f:
            seed_sql = f.read()
        
        conn.execute(seed_sql)
        conn.commit()
        
        conn.execute(seed_sql)
        conn.commit()
        
        # Verify counts are stable
        result = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()
        assert result["count"] == 3, "User count should be exactly 3 after idempotent seed"

class TestTimestampDefaults:
    """Test timestamp column defaults."""

    def test_created_at_defaults_to_now(self, clean_database: psycopg.Connection) -> None:
        """Verify created_at columns default to current timestamp."""
        conn = clean_database
        
        # Run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        conn.execute(up_sql)
        conn.commit()
        
        # Insert a user without specifying created_at
        conn.execute("""
            INSERT INTO users (oidc_sub, email, name, role)
            VALUES ('test-sub', 'test@example.com', 'Test User', 'viewer')
        """)
        conn.commit()
        
        result = conn.execute("""
            SELECT created_at, updated_at 
            FROM users 
            WHERE oidc_sub = 'test-sub'
        """).fetchone()
        
        assert result["created_at"] is not None, "created_at should have default value"
        assert result["updated_at"] is not None, "updated_at should have default value"

    def test_updated_at_trigger_works(self, clean_database: psycopg.Connection) -> None:
        """Verify updated_at is automatically updated on row modification."""
        conn = clean_database
        
        # Run up migration
        up_sql_path = get_sql_path("V0001.up.sql")
        with open(up_sql_path, "r") as f:
            up_sql = f.read()
        conn.execute(up_sql)
        conn.commit()
        
        # Insert a user
        conn.execute("""
            INSERT INTO users (oidc_sub, email, name, role)
            VALUES ('trigger-test-sub', 'trigger@example.com', 'Trigger Test', 'viewer')
        """)
        conn.commit()
        
        # Get initial updated_at
        result = conn.execute("""
            SELECT updated_at 
            FROM users 
            WHERE oidc_sub = 'trigger-test-sub'
        """).fetchone()
        initial_updated_at = result["updated_at"]
        
        # Update the user
        import time
        time.sleep(0.1)  # Small delay to ensure timestamp difference
        
        conn.execute("""
            UPDATE users 
            SET name = 'Updated Name' 
            WHERE oidc_sub = 'trigger-test-sub'
        """)
        conn.commit()
        
        # Get new updated_at
        result = conn.execute("""
            SELECT updated_at 
            FROM users 
            WHERE oidc_sub = 'trigger-test-sub'
        """).fetchone()
        new_updated_at = result["updated_at"]
        
        assert new_updated_at >= initial_updated_at, "updated_at should be updated by trigger"