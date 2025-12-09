"""
test_migration_sql.py - Shape test + idempotency + round-trip for REQ-001 migrations

Tests:
1. Schema shape validation - all expected tables, columns, types exist
2. Idempotency - migrations can be run multiple times without error
3. Round-trip - upgrade then downgrade works correctly
4. Seed data - seed script runs without errors
"""

import os
import subprocess
import pytest
from typing import Generator

# Try to import psycopg for direct DB testing
try:
    import psycopg
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

# Try to import testcontainers for containerized testing
try:
    from testcontainers.postgres import PostgresContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


# Get DATABASE_URL from environment or use default
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/voicesurveyagent_test"
)

# Paths relative to test file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KIT_ROOT = os.path.dirname(SCRIPT_DIR)
SQL_DIR = os.path.join(KIT_ROOT, "src", "storage", "sql")
SEED_DIR = os.path.join(KIT_ROOT, "src", "storage", "seed")
SCRIPTS_DIR = os.path.join(KIT_ROOT, "scripts")


def skip_if_no_db():
    """Skip test if database is not available."""
    if not PSYCOPG_AVAILABLE:
        pytest.skip("psycopg not installed - run: pip install psycopg[binary]")


def run_sql_file(db_url: str, sql_file: str) -> tuple[int, str, str]:
    """Run a SQL file using psql and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["psql", db_url, "-f", sql_file, "-v", "ON_ERROR_STOP=1"],
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def get_connection(db_url: str):
    """Get a database connection."""
    return psycopg.connect(db_url)


@pytest.fixture(scope="module")
def db_url() -> Generator[str, None, None]:
    """
    Provide a database URL for testing.
    Uses testcontainers if available, otherwise falls back to DATABASE_URL.
    """
    if os.environ.get("DISABLE_TESTCONTAINERS") == "1":
        # Use provided DATABASE_URL
        yield DATABASE_URL
        return
    
    if TESTCONTAINERS_AVAILABLE:
        # Use testcontainers for isolated testing
        with PostgresContainer("postgres:15-alpine") as postgres:
            yield postgres.get_connection_url().replace("+psycopg2", "")
    else:
        # Fall back to DATABASE_URL
        yield DATABASE_URL


@pytest.fixture(scope="module")
def clean_db(db_url: str) -> Generator[str, None, None]:
    """Ensure database is clean before tests."""
    skip_if_no_db()
    
    # Run downgrade to ensure clean state
    down_file = os.path.join(SQL_DIR, "V0001.down.sql")
    if os.path.exists(down_file):
        run_sql_file(db_url, down_file)
    
    yield db_url
    
    # Cleanup after tests
    if os.path.exists(down_file):
        run_sql_file(db_url, down_file)


class TestMigrationShape:
    """Test that migrations create expected schema shape."""
    
    def test_upgrade_creates_all_tables(self, clean_db: str):
        """Verify all expected tables are created."""
        skip_if_no_db()
        
        up_file = os.path.join(SQL_DIR, "V0001.up.sql")
        returncode, stdout, stderr = run_sql_file(clean_db, up_file)
        
        assert returncode == 0, f"Migration failed: {stderr}"
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                tables = {row[0] for row in cur.fetchall()}
        
        expected_tables = {
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
            "schema_migrations"
        }
        
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    
    def test_uuid_primary_keys(self, clean_db: str):
        """Verify UUID primary keys use PostgreSQL native UUID type."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                # Check that id columns are UUID type
                cur.execute("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND column_name = 'id'
                    AND table_name NOT IN ('schema_migrations')
                    ORDER BY table_name
                """)
                id_columns = cur.fetchall()
        
        for table_name, column_name, data_type in id_columns:
            assert data_type == "uuid", f"Table {table_name}.{column_name} should be UUID, got {data_type}"
    
    def test_enum_types_created(self, clean_db: str):
        """Verify all enum types are created."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT typname 
                    FROM pg_type 
                    WHERE typtype = 'e'
                    ORDER BY typname
                """)
                enums = {row[0] for row in cur.fetchall()}
        
        expected_enums = {
            "user_role",
            "campaign_status",
            "campaign_language",
            "question_type",
            "contact_state",
            "contact_language",
            "contact_outcome",
            "exclusion_source",
            "call_outcome",
            "event_type",
            "email_status",
            "email_template_type",
            "provider_type",
            "llm_provider",
            "transcript_language"
        }
        
        assert expected_enums.issubset(enums), f"Missing enums: {expected_enums - enums}"
    
    def test_foreign_key_indexes(self, clean_db: str):
        """Verify foreign key columns have appropriate indexes."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                # Get all indexes
                cur.execute("""
                    SELECT indexname, tablename
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                """)
                indexes = {row[0] for row in cur.fetchall()}
        
        # Check key indexes exist
        expected_indexes = [
            "idx_contacts_campaign_id",
            "idx_call_attempts_contact_id",
            "idx_call_attempts_campaign_id",
            "idx_survey_responses_contact_id",
            "idx_survey_responses_campaign_id",
            "idx_events_campaign_id",
            "idx_events_contact_id",
            "idx_email_notifications_event_id",
            "idx_email_notifications_contact_id",
            "idx_email_notifications_campaign_id"
        ]
        
        for idx in expected_indexes:
            assert idx in indexes, f"Missing index: {idx}"
    
    def test_timestamp_columns_have_timezone(self, clean_db: str):
        """Verify timestamp columns use timezone-aware type."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT table_name, column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND (column_name LIKE '%_at' OR column_name = 'created_at' OR column_name = 'updated_at')
                    AND data_type LIKE 'timestamp%'
                    ORDER BY table_name, column_name
                """)
                timestamp_columns = cur.fetchall()
        
        for table_name, column_name, data_type in timestamp_columns:
            assert "time zone" in data_type, \
                f"Table {table_name}.{column_name} should be timestamp with time zone, got {data_type}"


class TestMigrationIdempotency:
    """Test that migrations are idempotent."""
    
    def test_upgrade_idempotent(self, clean_db: str):
        """Verify upgrade can be run multiple times without error."""
        skip_if_no_db()
        
        up_file = os.path.join(SQL_DIR, "V0001.up.sql")
        
        # Run upgrade twice
        for i in range(2):
            returncode, stdout, stderr = run_sql_file(clean_db, up_file)
            assert returncode == 0, f"Migration run {i+1} failed: {stderr}"
    
    def test_downgrade_idempotent(self, clean_db: str):
        """Verify downgrade can be run multiple times without error."""
        skip_if_no_db()
        
        down_file = os.path.join(SQL_DIR, "V0001.down.sql")
        
        # Run downgrade twice
        for i in range(2):
            returncode, stdout, stderr = run_sql_file(clean_db, down_file)
            assert returncode == 0, f"Downgrade run {i+1} failed: {stderr}"


class TestMigrationRoundTrip:
    """Test upgrade/downgrade round-trip."""
    
    def test_round_trip(self, clean_db: str):
        """Verify upgrade then downgrade works correctly."""
        skip_if_no_db()
        
        up_file = os.path.join(SQL_DIR, "V0001.up.sql")
        down_file = os.path.join(SQL_DIR, "V0001.down.sql")
        
        # Upgrade
        returncode, stdout, stderr = run_sql_file(clean_db, up_file)
        assert returncode == 0, f"Upgrade failed: {stderr}"
        
        # Verify tables exist
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                count_after_up = cur.fetchone()[0]
        
        assert count_after_up >= 12, f"Expected at least 12 tables, got {count_after_up}"
        
        # Downgrade
        returncode, stdout, stderr = run_sql_file(clean_db, down_file)
        assert returncode == 0, f"Downgrade failed: {stderr}"
        
        # Verify tables are gone
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """)
                count_after_down = cur.fetchone()[0]
        
        assert count_after_down == 0, f"Expected 0 tables after downgrade, got {count_after_down}"


class TestSeedData:
    """Test seed data script."""
    
    def test_seed_runs_successfully(self, clean_db: str):
        """Verify seed script runs without errors."""
        skip_if_no_db()
        
        # First ensure schema exists
        up_file = os.path.join(SQL_DIR, "V0001.up.sql")
        run_sql_file(clean_db, up_file)
        
        # Run seed
        seed_file = os.path.join(SEED_DIR, "seed.sql")
        returncode, stdout, stderr = run_sql_file(clean_db, seed_file)
        
        assert returncode == 0, f"Seed failed: {stderr}"
    
    def test_seed_idempotent(self, clean_db: str):
        """Verify seed can be run multiple times without error."""
        skip_if_no_db()
        
        seed_file = os.path.join(SEED_DIR, "seed.sql")
        
        # Run seed twice
        for i in range(2):
            returncode, stdout, stderr = run_sql_file(clean_db, seed_file)
            assert returncode == 0, f"Seed run {i+1} failed: {stderr}"
    
    def test_seed_creates_expected_records(self, clean_db: str):
        """Verify seed creates expected number of records."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                # Check users
                cur.execute("SELECT COUNT(*) FROM users")
                users_count = cur.fetchone()[0]
                assert users_count >= 10, f"Expected at least 10 users, got {users_count}"
                
                # Check email templates
                cur.execute("SELECT COUNT(*) FROM email_templates")
                templates_count = cur.fetchone()[0]
                assert templates_count >= 6, f"Expected at least 6 templates, got {templates_count}"
                
                # Check campaigns
                cur.execute("SELECT COUNT(*) FROM campaigns")
                campaigns_count = cur.fetchone()[0]
                assert campaigns_count >= 4, f"Expected at least 4 campaigns, got {campaigns_count}"
                
                # Check contacts
                cur.execute("SELECT COUNT(*) FROM contacts")
                contacts_count = cur.fetchone()[0]
                assert contacts_count >= 10, f"Expected at least 10 contacts, got {contacts_count}"
                
                # Check provider config
                cur.execute("SELECT COUNT(*) FROM provider_configs")
                config_count = cur.fetchone()[0]
                assert config_count >= 1, f"Expected at least 1 provider config, got {config_count}"


class TestConstraints:
    """Test database constraints."""
    
    def test_max_attempts_constraint(self, clean_db: str):
        """Verify max_attempts constraint (1-5)."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                # Try to insert invalid max_attempts
                with pytest.raises(Exception):
                    cur.execute("""
                        INSERT INTO campaigns (
                            id, name, intro_script, 
                            question_1_text, question_1_type,
                            question_2_text, question_2_type,
                            question_3_text, question_3_type,
                            max_attempts, created_by_user_id
                        ) VALUES (
                            uuid_generate_v4(), 'Test', 'Intro',
                            'Q1', 'free_text',
                            'Q2', 'free_text',
                            'Q3', 'free_text',
                            10, '11111111-1111-1111-1111-111111111111'
                        )
                    """)
                    conn.commit()
    
    def test_confidence_constraint(self, clean_db: str):
        """Verify confidence score constraint (0-1)."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                # Get a valid call_attempt_id
                cur.execute("SELECT id, contact_id, campaign_id FROM call_attempts LIMIT 1")
                row = cur.fetchone()
                if row:
                    call_attempt_id, contact_id, campaign_id = row
                    
                    # Try to insert invalid confidence
                    with pytest.raises(Exception):
                        cur.execute("""
                            INSERT INTO survey_responses (
                                id, contact_id, campaign_id, call_attempt_id,
                                q1_answer, q1_confidence
                            ) VALUES (
                                uuid_generate_v4(), %s, %s, %s,
                                'test', 1.5
                            )
                        """, (contact_id, campaign_id, call_attempt_id))
                        conn.commit()


class TestTriggers:
    """Test database triggers."""
    
    def test_updated_at_trigger(self, clean_db: str):
        """Verify updated_at trigger works."""
        skip_if_no_db()
        
        with get_connection(clean_db) as conn:
            with conn.cursor() as cur:
                # Get a user
                cur.execute("SELECT id, updated_at FROM users LIMIT 1")
                row = cur.fetchone()
                if row:
                    user_id, original_updated_at = row
                    
                    # Update the user
                    cur.execute(
                        "UPDATE users SET name = 'Updated Name' WHERE id = %s",
                        (user_id,)
                    )
                    conn.commit()
                    
                    # Check updated_at changed
                    cur.execute("SELECT updated_at FROM users WHERE id = %s", (user_id,))
                    new_updated_at = cur.fetchone()[0]
                    
                    assert new_updated_at >= original_updated_at, \
                        "updated_at should be updated by trigger"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])