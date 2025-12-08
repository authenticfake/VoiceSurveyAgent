"""
test_migration_sql.py - Shape test + idempotency + round-trip for REQ-001 migrations

Tests:
1. Schema shape validation - all expected tables, columns, indexes exist
2. Idempotency - migrations can be run multiple times without error
3. Round-trip - upgrade then downgrade leaves clean state
"""

import os
import subprocess
import pytest
from typing import Generator

# Try to import testing dependencies
try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    from testcontainers.postgres import PostgresContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


# Skip all tests if dependencies not available
pytestmark = pytest.mark.skipif(
    not PSYCOPG2_AVAILABLE,
    reason="psycopg2 not installed - run: pip install psycopg2-binary"
)


def get_database_url() -> str | None:
    """Get database URL from environment or return None."""
    return os.environ.get("DATABASE_URL")


def run_sql_file(db_url: str, sql_file: str) -> None:
    """Execute a SQL file against the database."""
    result = subprocess.run(
        ["psql", db_url, "-f", sql_file],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"SQL execution failed: {result.stderr}")


@pytest.fixture(scope="module")
def database_url() -> Generator[str, None, None]:
    """
    Provide a database URL for testing.
    
    Priority:
    1. Use DISABLE_TESTCONTAINERS=1 + DATABASE_URL for local/CI Postgres
    2. Use testcontainers if available
    3. Skip tests if neither available
    """
    disable_tc = os.environ.get("DISABLE_TESTCONTAINERS", "0") == "1"
    env_url = get_database_url()
    
    if disable_tc and env_url:
        # Use provided DATABASE_URL
        yield env_url
        return
    
    if TESTCONTAINERS_AVAILABLE and not disable_tc:
        # Use testcontainers
        with PostgresContainer("postgres:15-alpine") as postgres:
            yield postgres.get_connection_url()
            return
    
    if env_url:
        # Fallback to DATABASE_URL without testcontainers
        yield env_url
        return
    
    pytest.skip(
        "No database available. Either:\n"
        "1. Set DATABASE_URL environment variable, or\n"
        "2. Install testcontainers: pip install testcontainers[postgres]"
    )


@pytest.fixture(scope="module")
def db_connection(database_url: str):
    """Create a database connection for testing."""
    conn = psycopg2.connect(database_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def migrated_db(database_url: str, db_connection) -> str:
    """Apply migrations and return database URL."""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
    
    # Run upgrade migration
    run_sql_file(database_url, up_sql)
    
    return database_url


class TestSchemaShape:
    """Test that schema has expected structure."""
    
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
    
    def test_all_tables_exist(self, migrated_db: str, db_connection):
        """Verify all expected tables are created."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        tables = {row[0] for row in cursor.fetchall()}
        cursor.close()
        
        for table in self.EXPECTED_TABLES:
            assert table in tables, f"Table '{table}' not found in schema"
    
    def test_all_enums_exist(self, migrated_db: str, db_connection):
        """Verify all expected enum types are created."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT typname 
            FROM pg_type 
            WHERE typtype = 'e'
        """)
        enums = {row[0] for row in cursor.fetchall()}
        cursor.close()
        
        for enum in self.EXPECTED_ENUMS:
            assert enum in enums, f"Enum type '{enum}' not found"
    
    def test_users_table_columns(self, migrated_db: str, db_connection):
        """Verify users table has correct columns."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
        """)
        columns = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        cursor.close()
        
        assert "id" in columns
        assert "oidc_sub" in columns
        assert "email" in columns
        assert "name" in columns
        assert "role" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
    
    def test_uuid_primary_keys(self, migrated_db: str, db_connection):
        """Verify UUID primary keys are used."""
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT c.column_name, c.data_type
            FROM information_schema.columns c
            JOIN information_schema.table_constraints tc 
                ON c.table_name = tc.table_name
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name 
                AND c.column_name = kcu.column_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND c.table_schema = 'public'
        """)
        pk_columns = cursor.fetchall()
        cursor.close()
        
        for col_name, data_type in pk_columns:
            assert data_type == "uuid", f"Primary key '{col_name}' should be UUID, got {data_type}"
    
    def test_foreign_key_indexes(self, migrated_db: str, db_connection):
        """Verify foreign key columns have indexes."""
        cursor = db_connection.cursor()
        
        # Get all foreign key columns
        cursor.execute("""
            SELECT 
                kcu.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
        """)
        fk_columns = cursor.fetchall()
        
        # Get all indexed columns
        cursor.execute("""
            SELECT 
                t.relname as table_name,
                a.attname as column_name
            FROM pg_index i
            JOIN pg_class t ON t.oid = i.indrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
            WHERE t.relnamespace = 'public'::regnamespace
        """)
        indexed_columns = {(row[0], row[1]) for row in cursor.fetchall()}
        cursor.close()
        
        for table, column in fk_columns:
            assert (table, column) in indexed_columns, \
                f"Foreign key column '{table}.{column}' should have an index"


class TestIdempotency:
    """Test that migrations are idempotent."""
    
    def test_upgrade_idempotent(self, database_url: str, db_connection):
        """Running upgrade twice should not fail."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        # First run already done by migrated_db fixture
        # Run again - should not fail due to IF NOT EXISTS
        run_sql_file(database_url, up_sql)
        
        # Verify tables still exist
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        
        assert count >= 11, "Tables should still exist after second migration run"


class TestRoundTrip:
    """Test upgrade/downgrade round-trip."""
    
    def test_downgrade_cleans_schema(self, database_url: str, db_connection):
        """Downgrade should remove all created objects."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        down_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.down.sql")
        
        # Run downgrade
        run_sql_file(database_url, down_sql)
        
        # Verify tables are gone
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        expected_removed = [
            "users", "campaigns", "contacts", "call_attempts",
            "survey_responses", "events", "email_notifications"
        ]
        for table in expected_removed:
            assert table not in tables, f"Table '{table}' should be removed after downgrade"
    
    def test_upgrade_after_downgrade(self, database_url: str, db_connection):
        """Should be able to upgrade again after downgrade."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        # Run upgrade again
        run_sql_file(database_url, up_sql)
        
        # Verify tables exist
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        count = cursor.fetchone()[0]
        cursor.close()
        
        assert count >= 11, "Tables should be recreated after upgrade"


class TestSeedData:
    """Test seed data application."""
    
    def test_seed_data_applies(self, database_url: str, db_connection):
        """Seed data should apply without errors."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seed_sql = os.path.join(script_dir, "src", "storage", "seed", "seed.sql")
        
        # Run seed
        run_sql_file(database_url, seed_sql)
        
        # Verify seed data exists
        cursor = db_connection.cursor()
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        assert cursor.fetchone()[0] >= 3, "Should have at least 3 seeded users"
        
        # Check email templates
        cursor.execute("SELECT COUNT(*) FROM email_templates")
        assert cursor.fetchone()[0] >= 5, "Should have at least 5 seeded email templates"
        
        # Check provider config
        cursor.execute("SELECT COUNT(*) FROM provider_configs")
        assert cursor.fetchone()[0] >= 1, "Should have at least 1 provider config"
        
        cursor.close()
    
    def test_seed_data_idempotent(self, database_url: str, db_connection):
        """Running seed twice should not fail or duplicate data."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seed_sql = os.path.join(script_dir, "src", "storage", "seed", "seed.sql")
        
        # Run seed again
        run_sql_file(database_url, seed_sql)
        
        # Verify no duplicates
        cursor = db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE oidc_sub = 'admin-oidc-sub-001'")
        assert cursor.fetchone()[0] == 1, "Should have exactly 1 admin user (no duplicates)"
        cursor.close()