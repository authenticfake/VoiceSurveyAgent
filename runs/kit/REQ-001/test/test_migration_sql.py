"""
Test suite for database migrations.

Tests schema shape, idempotency, and round-trip (upgrade/downgrade) operations.
"""

import os
import subprocess
from pathlib import Path

import pytest

# Check for required packages
try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

try:
    from testcontainers.postgres import PostgresContainer
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

# Skip all tests if dependencies are missing
pytestmark = pytest.mark.skipif(
    not HAS_PSYCOPG2,
    reason="psycopg2 not installed"
)

@pytest.fixture(scope="module")
def db_connection():
    """
    Provide a database connection for testing.
    
    Uses testcontainers if available and DISABLE_TESTCONTAINERS is not set,
    otherwise falls back to DATABASE_URL environment variable.
    """
    disable_tc = os.environ.get("DISABLE_TESTCONTAINERS", "").lower() in ("1", "true", "yes")
    
    if HAS_TESTCONTAINERS and not disable_tc:
        # Use testcontainers
        with PostgresContainer("postgres:15-alpine") as postgres:
            conn = psycopg2.connect(
                host=postgres.get_container_host_ip(),
                port=postgres.get_exposed_port(5432),
                user=postgres.username,
                password=postgres.password,
                database=postgres.dbname,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            yield conn
            conn.close()
    else:
        # Fall back to DATABASE_URL
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            pytest.skip("No DATABASE_URL set and testcontainers not available/disabled")
        
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        yield conn
        conn.close()

@pytest.fixture
def clean_db(db_connection):
    """Ensure clean database state before each test."""
    cursor = db_connection.cursor()
    
    # Drop all tables and types if they exist
    cursor.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
            FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = 'public'::regnamespace AND typtype = 'e') LOOP
                EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    
    yield db_connection
    
    # Cleanup after test
    cursor.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
            FOR r IN (SELECT typname FROM pg_type WHERE typnamespace = 'public'::regnamespace AND typtype = 'e') LOOP
                EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
            END LOOP;
        END $$;
    """)

def get_sql_path(filename: str) -> Path:
    """Get path to SQL file."""
    return Path(__file__).parent.parent / "src" / "storage" / "sql" / filename

def get_seed_path() -> Path:
    """Get path to seed SQL file."""
    return Path(__file__).parent.parent / "src" / "storage" / "seed" / "seed.sql"

class TestSchemaShape:
    """Test that schema matches SPEC data model."""
    
    def test_all_tables_created(self, clean_db):
        """Verify all expected tables are created."""
        cursor = clean_db.cursor()
        
        # Apply up migration
        up_sql = get_sql_path("V0001.up.sql").read_text()
        cursor.execute(up_sql)
        
        # Check tables exist
        cursor.execute("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = {row[0] for row in cursor.fetchall()}
        
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
        }
        
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"
    
    def test_all_enums_created(self, clean_db):
        """Verify all expected enum types are created."""
        cursor = clean_db.cursor()
        
        # Apply up migration
        up_sql = get_sql_path("V0001.up.sql").read_text()
        cursor.execute(up_sql)
        
        # Check enum types exist
        cursor.execute("""
            SELECT typname FROM pg_type 
            WHERE typnamespace = 'public'::regnamespace 
            AND typtype = 'e'
            ORDER BY typname;
        """)
        enums = {row[0] for row in cursor.fetchall()}
        
        expected_enums = {
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
        }
        
        assert expected_enums.issubset(enums), f"Missing enums: {expected_enums - enums}"
    
    def test_uuid_primary_keys(self, clean_db):
        """Verify UUID primary keys are used."""
        cursor = clean_db.cursor()
        
        # Apply up migration
        up_sql = get_sql_path("V0001.up.sql").read_text()
        cursor.execute(up_sql)
        
        # Check primary key types
        cursor.execute("""
            SELECT c.table_name, c.column_name, c.data_type
            FROM information_schema.columns c
            JOIN information_schema.table_constraints tc 
                ON c.table_name = tc.table_name 
                AND tc.constraint_type = 'PRIMARY KEY'
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name 
                AND c.column_name = kcu.column_name
            WHERE c.table_schema = 'public';
        """)
        
        for table_name, column_name, data_type in cursor.fetchall():
            assert data_type == "uuid", f"Table {table_name} has non-UUID primary key: {data_type}"
    
    def test_foreign_key_indexes(self, clean_db):
        """Verify foreign key columns have indexes."""
        cursor = clean_db.cursor()
        
        # Apply up migration
        up_sql = get_sql_path("V0001.up.sql").read_text()
        cursor.execute(up_sql)
        
        # Get all foreign key columns
        cursor.execute("""
            SELECT
                tc.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public';
        """)
        fk_columns = cursor.fetchall()
        
        # Check each FK column has an index
        for table_name, column_name in fk_columns:
            cursor.execute("""
                SELECT 1 FROM pg_indexes
                WHERE tablename = %s
                AND indexdef LIKE %s;
            """, (table_name, f"%{column_name}%"))
            
            assert cursor.fetchone() is not None, \
                f"Missing index on foreign key {table_name}.{column_name}"

class TestIdempotency:
    """Test that migrations are idempotent."""
    
    def test_up_migration_idempotent(self, clean_db):
        """Verify up migration can be run multiple times."""
        cursor = clean_db.cursor()
        
        up_sql = get_sql_path("V0001.up.sql").read_text()
        
        # Run migration twice
        cursor.execute(up_sql)
        cursor.execute(up_sql)  # Should not raise
        
        # Verify tables still exist
        cursor.execute("""
            SELECT COUNT(*) FROM pg_tables 
            WHERE schemaname = 'public';
        """)
        assert cursor.fetchone()[0] > 0
    
    def test_seed_idempotent(self, clean_db):
        """Verify seed data can be applied multiple times."""
        cursor = clean_db.cursor()
        
        # Apply schema first
        up_sql = get_sql_path("V0001.up.sql").read_text()
        cursor.execute(up_sql)
        
        # Apply seed twice
        seed_sql = get_seed_path().read_text()
        cursor.execute(seed_sql)
        cursor.execute(seed_sql)  # Should not raise
        
        # Verify data exists
        cursor.execute("SELECT COUNT(*) FROM users;")
        assert cursor.fetchone()[0] == 3

class TestRoundTrip:
    """Test upgrade/downgrade round-trip."""
    
    def test_upgrade_downgrade_upgrade(self, clean_db):
        """Verify schema can be upgraded, downgraded, and upgraded again."""
        cursor = clean_db.cursor()
        
        up_sql = get_sql_path("V0001.up.sql").read_text()
        down_sql = get_sql_path("V0001.down.sql").read_text()
        
        # Upgrade
        cursor.execute(up_sql)
        cursor.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';")
        tables_after_up = cursor.fetchone()[0]
        assert tables_after_up > 0
        
        # Downgrade
        cursor.execute(down_sql)
        cursor.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';")
        tables_after_down = cursor.fetchone()[0]
        assert tables_after_down == 0
        
        # Upgrade again
        cursor.execute(up_sql)
        cursor.execute("SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';")
        tables_after_reup = cursor.fetchone()[0]
        assert tables_after_reup == tables_after_up
    
    def test_downgrade_removes_all_objects(self, clean_db):
        """Verify downgrade removes all database objects."""
        cursor = clean_db.cursor()
        
        up_sql = get_sql_path("V0001.up.sql").read_text()
        down_sql = get_sql_path("V0001.down.sql").read_text()
        
        # Upgrade then downgrade
        cursor.execute(up_sql)
        cursor.execute(down_sql)
        
        # Check no tables remain
        cursor.execute("""
            SELECT COUNT(*) FROM pg_tables 
            WHERE schemaname = 'public';
        """)
        assert cursor.fetchone()[0] == 0
        
        # Check no custom types remain
        cursor.execute("""
            SELECT COUNT(*) FROM pg_type 
            WHERE typnamespace = 'public'::regnamespace 
            AND typtype = 'e';
        """)
        assert cursor.fetchone()[0] == 0

class TestSeedData:
    """Test seed data validity."""
    
    def test_seed_creates_minimum_records(self, clean_db):
        """Verify seed creates at least 10 records total."""
        cursor = clean_db.cursor()
        
        # Apply schema and seed
        up_sql = get_sql_path("V0001.up.sql").read_text()
        seed_sql = get_seed_path().read_text()
        cursor.execute(up_sql)
        cursor.execute(seed_sql)
        
        # Count total records
        total = 0
        for table in ["users", "email_templates", "provider_configs", "campaigns", "contacts", "exclusion_list_entries"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            total += cursor.fetchone()[0]
        
        assert total >= 10, f"Seed data has only {total} records, expected at least 10"
    
    def test_seed_creates_maximum_records(self, clean_db):
        """Verify seed creates no more than 20 records total."""
        cursor = clean_db.cursor()
        
        # Apply schema and seed
        up_sql = get_sql_path("V0001.up.sql").read_text()
        seed_sql = get_seed_path().read_text()
        cursor.execute(up_sql)
        cursor.execute(seed_sql)
        
        # Count total records
        total = 0
        for table in ["users", "email_templates", "provider_configs", "campaigns", "contacts", "exclusion_list_entries"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            total += cursor.fetchone()[0]
        
        assert total <= 20, f"Seed data has {total} records, expected at most 20"
    
    def test_seed_foreign_keys_valid(self, clean_db):
        """Verify seed data has valid foreign key references."""
        cursor = clean_db.cursor()
        
        # Apply schema and seed
        up_sql = get_sql_path("V0001.up.sql").read_text()
        seed_sql = get_seed_path().read_text()
        cursor.execute(up_sql)
        cursor.execute(seed_sql)
        
        # Check campaign references valid user
        cursor.execute("""
            SELECT c.id FROM campaigns c
            LEFT JOIN users u ON c.created_by_user_id = u.id
            WHERE u.id IS NULL;
        """)
        orphan_campaigns = cursor.fetchall()
        assert len(orphan_campaigns) == 0, "Found campaigns with invalid user references"
        
        # Check contacts reference valid campaign
        cursor.execute("""
            SELECT ct.id FROM contacts ct
            LEFT JOIN campaigns c ON ct.campaign_id = c.id
            WHERE c.id IS NULL;
        """)
        orphan_contacts = cursor.fetchall()
        assert len(orphan_contacts) == 0, "Found contacts with invalid campaign references"