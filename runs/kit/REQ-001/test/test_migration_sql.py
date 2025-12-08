"""
Test suite for REQ-001: Database schema and migrations
Tests shape validation, idempotency, and round-trip migrations
"""

import os
import subprocess
import pytest
from typing import Generator

# Try to import testing dependencies
try:
    import psycopg2
    from psycopg2.extensions import connection as PgConnection
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from testcontainers.postgres import PostgresContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False

# Skip all tests if psycopg2 is not available
pytestmark = pytest.mark.skipif(
    not PSYCOPG2_AVAILABLE,
    reason="psycopg2 not installed"
)

def get_database_url() -> str | None:
    """Get database URL from environment or return None."""
    return os.environ.get("DATABASE_URL")

def run_sql_file(conn: "PgConnection", filepath: str) -> None:
    """Execute a SQL file against the database."""
    with open(filepath, "r") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()

def get_sql_dir() -> str:
    """Get the SQL directory path."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "storage",
        "sql"
    )

def get_seed_dir() -> str:
    """Get the seed directory path."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "storage",
        "seed"
    )

@pytest.fixture(scope="module")
def database_connection() -> Generator["PgConnection", None, None]:
    """
    Provide a database connection for testing.
    Uses testcontainers if available, otherwise falls back to DATABASE_URL.
    """
    db_url = get_database_url()
    
    if TESTCONTAINERS_AVAILABLE and not db_url:
        # Use testcontainers
        with PostgresContainer("postgres:15") as postgres:
            conn = psycopg2.connect(
                host=postgres.get_container_host_ip(),
                port=postgres.get_exposed_port(5432),
                user=postgres.username,
                password=postgres.password,
                database=postgres.dbname
            )
            yield conn
            conn.close()
    elif db_url:
        # Use provided DATABASE_URL
        conn = psycopg2.connect(db_url)
        yield conn
        conn.close()
    else:
        pytest.skip(
            "No database available. Set DATABASE_URL or install testcontainers."
        )

class TestSchemaShape:
    """Test that the schema has the expected shape."""

    def test_all_tables_exist(self, database_connection: "PgConnection") -> None:
        """Verify all expected tables are created."""
        # First apply the migration
        sql_dir = get_sql_dir()
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.up.sql"))
        
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
        
        with database_connection.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            actual_tables = {row[0] for row in cur.fetchall()}
        
        for table in expected_tables:
            assert table in actual_tables, f"Table {table} not found"

    def test_all_enum_types_exist(self, database_connection: "PgConnection") -> None:
        """Verify all expected enum types are created."""
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
        
        with database_connection.cursor() as cur:
            cur.execute("""
                SELECT typname 
                FROM pg_type 
                WHERE typtype = 'e'
            """)
            actual_enums = {row[0] for row in cur.fetchall()}
        
        for enum in expected_enums:
            assert enum in actual_enums, f"Enum type {enum} not found"

    def test_uuid_primary_keys(self, database_connection: "PgConnection") -> None:
        """Verify all tables use UUID primary keys."""
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
        
        with database_connection.cursor() as cur:
            for table in tables_with_pk:
                cur.execute(f"""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    AND column_name = 'id'
                """)
                result = cur.fetchone()
                assert result is not None, f"No id column in {table}"
                assert result[0] == "uuid", f"Table {table} id is not UUID type"

    def test_foreign_key_indexes_exist(self, database_connection: "PgConnection") -> None:
        """Verify indexes exist on foreign key columns."""
        expected_indexes = [
            ("contacts", "idx_contacts_campaign_id"),
            ("call_attempts", "idx_call_attempts_contact_id"),
            ("call_attempts", "idx_call_attempts_campaign_id"),
            ("survey_responses", "idx_survey_responses_contact_id"),
            ("survey_responses", "idx_survey_responses_campaign_id"),
            ("events", "idx_events_campaign_id"),
            ("events", "idx_events_contact_id"),
            ("email_notifications", "idx_email_notifications_event_id"),
            ("email_notifications", "idx_email_notifications_contact_id"),
            ("email_notifications", "idx_email_notifications_campaign_id"),
        ]
        
        with database_connection.cursor() as cur:
            cur.execute("""
                SELECT tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            actual_indexes = {(row[0], row[1]) for row in cur.fetchall()}
        
        for table, index in expected_indexes:
            assert (table, index) in actual_indexes, \
                f"Index {index} not found on table {table}"

class TestMigrationIdempotency:
    """Test that migrations are idempotent."""

    def test_up_migration_idempotent(self, database_connection: "PgConnection") -> None:
        """Verify up migration can be run multiple times without error."""
        sql_dir = get_sql_dir()
        up_file = os.path.join(sql_dir, "V0001.up.sql")
        
        # Run migration twice - should not raise
        run_sql_file(database_connection, up_file)
        run_sql_file(database_connection, up_file)
        
        # Verify tables still exist
        with database_connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            count = cur.fetchone()[0]
            assert count >= 11, "Expected at least 11 tables"

    def test_seed_idempotent(self, database_connection: "PgConnection") -> None:
        """Verify seed data can be run multiple times without error."""
        seed_dir = get_seed_dir()
        seed_file = os.path.join(seed_dir, "seed.sql")
        
        # Run seed twice - should not raise
        run_sql_file(database_connection, seed_file)
        run_sql_file(database_connection, seed_file)
        
        # Verify expected seed data exists
        with database_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            user_count = cur.fetchone()[0]
            assert user_count == 3, "Expected 3 seeded users"
            
            cur.execute("SELECT COUNT(*) FROM email_templates")
            template_count = cur.fetchone()[0]
            assert template_count == 6, "Expected 6 seeded email templates"

class TestMigrationRoundTrip:
    """Test migration up/down round-trip."""

    def test_down_migration_removes_all(self, database_connection: "PgConnection") -> None:
        """Verify down migration removes all objects."""
        sql_dir = get_sql_dir()
        
        # Apply up migration
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.up.sql"))
        
        # Apply down migration
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.down.sql"))
        
        # Verify tables are removed
        with database_connection.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            # These tables should not exist after down migration
            removed_tables = [
                "users", "campaigns", "contacts", "call_attempts",
                "survey_responses", "events", "email_notifications"
            ]
            for table in removed_tables:
                assert table not in tables, f"Table {table} should be removed"

    def test_round_trip_migration(self, database_connection: "PgConnection") -> None:
        """Verify up -> down -> up migration cycle works."""
        sql_dir = get_sql_dir()
        
        # Up
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.up.sql"))
        
        # Down
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.down.sql"))
        
        # Up again
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.up.sql"))
        
        # Verify schema is intact
        with database_connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            count = cur.fetchone()[0]
            assert count >= 11, "Expected at least 11 tables after round-trip"

class TestConstraints:
    """Test database constraints are properly enforced."""

    def test_max_attempts_constraint(self, database_connection: "PgConnection") -> None:
        """Verify max_attempts constraint (1-5) is enforced."""
        sql_dir = get_sql_dir()
        seed_dir = get_seed_dir()
        
        # Ensure schema and seed data exist
        run_sql_file(database_connection, os.path.join(sql_dir, "V0001.up.sql"))
        run_sql_file(database_connection, os.path.join(seed_dir, "seed.sql"))
        
        with database_connection.cursor() as cur:
            # Try to insert campaign with invalid max_attempts
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute("""
                    INSERT INTO campaigns (
                        name, intro_script, 
                        question_1_text, question_1_type,
                        question_2_text, question_2_type,
                        question_3_text, question_3_type,
                        max_attempts, created_by_user_id
                    ) VALUES (
                        'Test', 'Intro',
                        'Q1', 'free_text',
                        'Q2', 'free_text',
                        'Q3', 'free_text',
                        6, '00000000-0000-0000-0000-000000000001'
                    )
                """)
        database_connection.rollback()

    def test_unique_constraints(self, database_connection: "PgConnection") -> None:
        """Verify unique constraints are enforced."""
        with database_connection.cursor() as cur:
            # Try to insert duplicate oidc_sub
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cur.execute("""
                    INSERT INTO users (oidc_sub, email, name, role)
                    VALUES ('admin-oidc-sub-001', 'different@email.com', 'Dup', 'viewer')
                """)
        database_connection.rollback()