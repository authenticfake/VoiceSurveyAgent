"""
test_migration_sql.py - Shape test + idempotency + round-trip for REQ-001 migrations

Tests:
1. Schema shape validation - all expected tables and columns exist
2. Idempotency - migrations can be run multiple times without error
3. Round-trip - upgrade then downgrade works correctly
4. Enum types are created correctly
5. Indexes exist for foreign keys and query performance
"""

import os
import subprocess
import pytest
from typing import Generator, Any

# Try to import testing dependencies
try:
    import psycopg2
    from psycopg2.extensions import connection as PgConnection
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    PgConnection = Any

try:
    from testcontainers.postgres import PostgresContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


# Skip all tests if dependencies not available
pytestmark = pytest.mark.skipif(
    not PSYCOPG2_AVAILABLE,
    reason="psycopg2 not installed"
)


def get_database_url() -> str:
    """Get database URL from environment or None if not set."""
    return os.environ.get("DATABASE_URL", "")


def can_use_testcontainers() -> bool:
    """Check if testcontainers can be used."""
    if not TESTCONTAINERS_AVAILABLE:
        return False
    # Check if Docker is available
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="module")
def database_connection() -> Generator[PgConnection, None, None]:
    """
    Provide a database connection for testing.
    Uses testcontainers if Docker is available, otherwise falls back to DATABASE_URL.
    """
    db_url = get_database_url()
    
    if can_use_testcontainers():
        # Use testcontainers
        with PostgresContainer("postgres:15-alpine") as postgres:
            conn = psycopg2.connect(postgres.get_connection_url())
            conn.autocommit = True
            yield conn
            conn.close()
    elif db_url:
        # Use provided DATABASE_URL
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        yield conn
        conn.close()
    else:
        pytest.skip("No database available: set DATABASE_URL or install Docker for testcontainers")


@pytest.fixture
def clean_database(database_connection: PgConnection) -> Generator[PgConnection, None, None]:
    """Ensure database is clean before each test."""
    cursor = database_connection.cursor()
    
    # Run downgrade to clean state
    sql_dir = os.path.join(os.path.dirname(__file__), "..", "src", "storage", "sql")
    down_file = os.path.join(sql_dir, "V0001.down.sql")
    
    if os.path.exists(down_file):
        with open(down_file, "r") as f:
            try:
                cursor.execute(f.read())
            except psycopg2.Error:
                # Ignore errors if tables don't exist
                database_connection.rollback()
    
    cursor.close()
    yield database_connection


def run_migration(conn: PgConnection, migration_file: str) -> None:
    """Execute a migration file against the database."""
    cursor = conn.cursor()
    with open(migration_file, "r") as f:
        cursor.execute(f.read())
    cursor.close()


def get_sql_path(filename: str) -> str:
    """Get the full path to a SQL file."""
    return os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "storage",
        "sql",
        filename
    )


class TestSchemaShape:
    """Test that the schema has the expected shape."""
    
    EXPECTED_TABLES = [
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
    
    EXPECTED_ENUMS = [
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
    
    def test_all_tables_created(self, clean_database: PgConnection) -> None:
        """Verify all expected tables are created."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        tables = {row[0] for row in cursor.fetchall()}
        cursor.close()
        
        for expected_table in self.EXPECTED_TABLES:
            assert expected_table in tables, f"Table {expected_table} not found"
    
    def test_all_enums_created(self, clean_database: PgConnection) -> None:
        """Verify all expected enum types are created."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        cursor.execute("""
            SELECT typname 
            FROM pg_type 
            WHERE typtype = 'e'
        """)
        enums = {row[0] for row in cursor.fetchall()}
        cursor.close()
        
        for expected_enum in self.EXPECTED_ENUMS:
            assert expected_enum in enums, f"Enum {expected_enum} not found"
    
    def test_uuid_primary_keys(self, clean_database: PgConnection) -> None:
        """Verify all tables use UUID primary keys."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        
        for table in self.EXPECTED_TABLES:
            cursor.execute(f"""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}' 
                AND column_name = 'id'
            """)
            result = cursor.fetchone()
            assert result is not None, f"Table {table} has no id column"
            assert result[0] == "uuid", f"Table {table} id is not UUID type"
        
        cursor.close()
    
    def test_timestamp_columns_have_timezone(self, clean_database: PgConnection) -> None:
        """Verify timestamp columns use timezone-aware type."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        cursor.execute("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public'
            AND (column_name LIKE '%_at' OR column_name LIKE '%_time')
            AND data_type LIKE 'timestamp%'
        """)
        
        for row in cursor.fetchall():
            table, column, dtype = row
            assert dtype == "timestamp with time zone", \
                f"{table}.{column} should be timestamp with time zone, got {dtype}"
        
        cursor.close()


class TestForeignKeyIndexes:
    """Test that foreign key columns have appropriate indexes."""
    
    FK_COLUMNS = [
        ("campaigns", "created_by_user_id"),
        ("campaigns", "email_completed_template_id"),
        ("campaigns", "email_refused_template_id"),
        ("campaigns", "email_not_reached_template_id"),
        ("contacts", "campaign_id"),
        ("call_attempts", "contact_id"),
        ("call_attempts", "campaign_id"),
        ("survey_responses", "contact_id"),
        ("survey_responses", "campaign_id"),
        ("survey_responses", "call_attempt_id"),
        ("events", "campaign_id"),
        ("events", "contact_id"),
        ("events", "call_attempt_id"),
        ("email_notifications", "event_id"),
        ("email_notifications", "contact_id"),
        ("email_notifications", "campaign_id"),
        ("email_notifications", "template_id"),
        ("transcript_snippets", "call_attempt_id"),
    ]
    
    def test_foreign_key_indexes_exist(self, clean_database: PgConnection) -> None:
        """Verify indexes exist for foreign key columns."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        
        for table, column in self.FK_COLUMNS:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE tablename = %s 
                AND indexdef LIKE %s
            """, (table, f"%{column}%"))
            
            count = cursor.fetchone()[0]
            assert count > 0, f"No index found for {table}.{column}"
        
        cursor.close()


class TestIdempotency:
    """Test that migrations are idempotent."""
    
    def test_upgrade_idempotent(self, clean_database: PgConnection) -> None:
        """Verify upgrade migration can be run multiple times."""
        up_file = get_sql_path("V0001.up.sql")
        
        # Run upgrade twice
        run_migration(clean_database, up_file)
        run_migration(clean_database, up_file)  # Should not raise
        
        # Verify tables still exist
        cursor = clean_database.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        
        assert count > 0, "Tables should exist after idempotent upgrade"
    
    def test_downgrade_idempotent(self, clean_database: PgConnection) -> None:
        """Verify downgrade migration can be run multiple times."""
        up_file = get_sql_path("V0001.up.sql")
        down_file = get_sql_path("V0001.down.sql")
        
        # Setup
        run_migration(clean_database, up_file)
        
        # Run downgrade twice
        run_migration(clean_database, down_file)
        run_migration(clean_database, down_file)  # Should not raise
        
        # Verify tables are gone
        cursor = clean_database.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        
        assert count == 0, "All tables should be dropped after downgrade"


class TestRoundTrip:
    """Test upgrade/downgrade round-trip."""
    
    def test_upgrade_downgrade_upgrade(self, clean_database: PgConnection) -> None:
        """Verify full round-trip: upgrade -> downgrade -> upgrade."""
        up_file = get_sql_path("V0001.up.sql")
        down_file = get_sql_path("V0001.down.sql")
        
        # First upgrade
        run_migration(clean_database, up_file)
        
        cursor = clean_database.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        initial_count = cursor.fetchone()[0]
        
        # Downgrade
        run_migration(clean_database, down_file)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        after_down = cursor.fetchone()[0]
        assert after_down == 0, "All tables should be dropped"
        
        # Second upgrade
        run_migration(clean_database, up_file)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        final_count = cursor.fetchone()[0]
        cursor.close()
        
        assert final_count == initial_count, "Table count should match after round-trip"


class TestSeedData:
    """Test seed data application."""
    
    def test_seed_is_idempotent(self, clean_database: PgConnection) -> None:
        """Verify seed data can be applied multiple times."""
        up_file = get_sql_path("V0001.up.sql")
        seed_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "storage",
            "seed",
            "seed.sql"
        )
        
        run_migration(clean_database, up_file)
        
        cursor = clean_database.cursor()
        
        # Apply seed twice
        with open(seed_file, "r") as f:
            seed_sql = f.read()
            cursor.execute(seed_sql)
            cursor.execute(seed_sql)  # Should not raise
        
        # Verify expected seed data exists
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        assert user_count >= 3, "Should have at least 3 seeded users"
        
        cursor.execute("SELECT COUNT(*) FROM email_templates")
        template_count = cursor.fetchone()[0]
        assert template_count >= 6, "Should have at least 6 seeded templates"
        
        cursor.execute("SELECT COUNT(*) FROM provider_configs")
        config_count = cursor.fetchone()[0]
        assert config_count >= 1, "Should have at least 1 provider config"
        
        cursor.execute("SELECT COUNT(*) FROM campaigns")
        campaign_count = cursor.fetchone()[0]
        assert campaign_count >= 1, "Should have at least 1 seeded campaign"
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        assert contact_count >= 5, "Should have at least 5 seeded contacts"
        
        cursor.close()
    
    def test_seed_data_values(self, clean_database: PgConnection) -> None:
        """Verify seed data has correct values."""
        up_file = get_sql_path("V0001.up.sql")
        seed_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "storage",
            "seed",
            "seed.sql"
        )
        
        run_migration(clean_database, up_file)
        
        cursor = clean_database.cursor()
        with open(seed_file, "r") as f:
            cursor.execute(f.read())
        
        # Check admin user exists with correct role
        cursor.execute("""
            SELECT role FROM users WHERE email = 'admin@voicesurvey.local'
        """)
        result = cursor.fetchone()
        assert result is not None, "Admin user should exist"
        assert result[0] == "admin", "Admin user should have admin role"
        
        # Check campaign has valid configuration
        cursor.execute("""
            SELECT max_attempts, status FROM campaigns 
            WHERE name = 'Customer Satisfaction Survey Q1 2025'
        """)
        result = cursor.fetchone()
        assert result is not None, "Sample campaign should exist"
        assert 1 <= result[0] <= 5, "max_attempts should be between 1 and 5"
        assert result[1] == "draft", "Campaign should be in draft status"
        
        cursor.close()


class TestConstraints:
    """Test database constraints."""
    
    def test_max_attempts_constraint(self, clean_database: PgConnection) -> None:
        """Verify max_attempts constraint (1-5)."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        
        # First create a user for the foreign key
        cursor.execute("""
            INSERT INTO users (oidc_sub, email, name, role)
            VALUES ('test-sub', 'test@test.com', 'Test', 'admin')
            RETURNING id
        """)
        user_id = cursor.fetchone()[0]
        
        # Try invalid max_attempts = 0
        with pytest.raises(psycopg2.Error):
            cursor.execute("""
                INSERT INTO campaigns (name, intro_script, 
                    question_1_text, question_1_type,
                    question_2_text, question_2_type,
                    question_3_text, question_3_type,
                    max_attempts, created_by_user_id)
                VALUES ('Test', 'Intro', 'Q1', 'free_text', 'Q2', 'numeric', 
                    'Q3', 'scale', 0, %s)
            """, (user_id,))
        
        clean_database.rollback()
        
        # Try invalid max_attempts = 6
        with pytest.raises(psycopg2.Error):
            cursor.execute("""
                INSERT INTO campaigns (name, intro_script,
                    question_1_text, question_1_type,
                    question_2_text, question_2_type,
                    question_3_text, question_3_type,
                    max_attempts, created_by_user_id)
                VALUES ('Test', 'Intro', 'Q1', 'free_text', 'Q2', 'numeric',
                    'Q3', 'scale', 6, %s)
            """, (user_id,))
        
        cursor.close()
    
    def test_confidence_constraint(self, clean_database: PgConnection) -> None:
        """Verify confidence score constraint (0-1)."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        seed_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "storage",
            "seed",
            "seed.sql"
        )
        
        cursor = clean_database.cursor()
        with open(seed_file, "r") as f:
            cursor.execute(f.read())
        
        # Get a contact and campaign for FK
        cursor.execute("SELECT id FROM contacts LIMIT 1")
        contact_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM campaigns LIMIT 1")
        campaign_id = cursor.fetchone()[0]
        
        # Create a call attempt
        cursor.execute("""
            INSERT INTO call_attempts (contact_id, campaign_id, attempt_number, call_id)
            VALUES (%s, %s, 1, 'test-call-001')
            RETURNING id
        """, (contact_id, campaign_id))
        call_attempt_id = cursor.fetchone()[0]
        
        # Try invalid confidence > 1
        with pytest.raises(psycopg2.Error):
            cursor.execute("""
                INSERT INTO survey_responses (contact_id, campaign_id, call_attempt_id, 
                    q1_answer, q1_confidence)
                VALUES (%s, %s, %s, 'Answer', 1.5)
            """, (contact_id, campaign_id, call_attempt_id))
        
        cursor.close()


class TestTriggers:
    """Test database triggers."""
    
    def test_updated_at_trigger(self, clean_database: PgConnection) -> None:
        """Verify updated_at is automatically updated."""
        run_migration(clean_database, get_sql_path("V0001.up.sql"))
        
        cursor = clean_database.cursor()
        
        # Insert a user
        cursor.execute("""
            INSERT INTO users (oidc_sub, email, name, role)
            VALUES ('trigger-test', 'trigger@test.com', 'Trigger Test', 'viewer')
            RETURNING id, created_at, updated_at
        """)
        user_id, created_at, initial_updated = cursor.fetchone()
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Update the user
        cursor.execute("""
            UPDATE users SET name = 'Updated Name' WHERE id = %s
            RETURNING updated_at
        """, (user_id,))
        new_updated = cursor.fetchone()[0]
        
        assert new_updated > initial_updated, "updated_at should be updated by trigger"
        
        cursor.close()