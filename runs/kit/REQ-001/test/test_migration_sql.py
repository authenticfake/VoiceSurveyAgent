"""
test_migration_sql.py - Shape test + idempotency + round-trip for REQ-001 migrations

Tests:
1. Schema shape matches SPEC data model
2. Migrations are idempotent (can run multiple times)
3. Round-trip (up -> down -> up) works correctly
4. All enum types are created
5. All indexes exist
6. Foreign key constraints are correct
"""

import os
import pytest
from typing import Generator
import psycopg2
from psycopg2.extensions import connection as PgConnection


# Skip if no database available
DATABASE_URL = os.environ.get("DATABASE_URL")
SKIP_REASON = "DATABASE_URL not set - skipping database tests"


def get_connection() -> PgConnection:
    """Get database connection from DATABASE_URL."""
    if not DATABASE_URL:
        pytest.skip(SKIP_REASON)
    return psycopg2.connect(DATABASE_URL)


def run_sql_file(conn: PgConnection, filepath: str) -> None:
    """Execute a SQL file."""
    with open(filepath, "r") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


@pytest.fixture
def db_connection() -> Generator[PgConnection, None, None]:
    """Provide a database connection for tests."""
    conn = get_connection()
    yield conn
    conn.close()


@pytest.fixture
def clean_db(db_connection: PgConnection) -> Generator[PgConnection, None, None]:
    """Ensure clean database state before and after tests."""
    # Get paths
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    down_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.down.sql")
    
    # Clean before test
    try:
        run_sql_file(db_connection, down_sql)
    except Exception:
        pass  # Tables might not exist yet
    
    yield db_connection
    
    # Clean after test
    try:
        run_sql_file(db_connection, down_sql)
    except Exception:
        pass


class TestMigrationShape:
    """Test that schema shape matches SPEC data model."""
    
    def test_all_tables_created(self, clean_db: PgConnection) -> None:
        """Verify all expected tables are created."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        run_sql_file(clean_db, up_sql)
        
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
        
        with clean_db.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            actual_tables = {row[0] for row in cur.fetchall()}
        
        for table in expected_tables:
            assert table in actual_tables, f"Table {table} not found"
    
    def test_all_enum_types_created(self, clean_db: PgConnection) -> None:
        """Verify all enum types are created."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        run_sql_file(clean_db, up_sql)
        
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
        
        with clean_db.cursor() as cur:
            cur.execute("""
                SELECT typname 
                FROM pg_type 
                WHERE typtype = 'e'
            """)
            actual_enums = {row[0] for row in cur.fetchall()}
        
        for enum in expected_enums:
            assert enum in actual_enums, f"Enum type {enum} not found"
    
    def test_uuid_primary_keys(self, clean_db: PgConnection) -> None:
        """Verify UUID primary keys use PostgreSQL native UUID type."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        run_sql_file(clean_db, up_sql)
        
        tables_with_uuid_pk = [
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
        
        with clean_db.cursor() as cur:
            for table in tables_with_uuid_pk:
                cur.execute(f"""
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    AND column_name = 'id'
                """)
                result = cur.fetchone()
                assert result is not None, f"Table {table} has no id column"
                assert result[0] == "uuid", f"Table {table} id is not UUID type"
    
    def test_foreign_key_indexes(self, clean_db: PgConnection) -> None:
        """Verify foreign key columns have appropriate indexes."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        run_sql_file(clean_db, up_sql)
        
        # Check key foreign key indexes exist
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
        ]
        
        with clean_db.cursor() as cur:
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            actual_indexes = {row[0] for row in cur.fetchall()}
        
        for index in expected_indexes:
            assert index in actual_indexes, f"Index {index} not found"


class TestMigrationIdempotency:
    """Test that migrations are idempotent."""
    
    def test_up_migration_idempotent(self, clean_db: PgConnection) -> None:
        """Verify up migration can run multiple times without error."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        
        # Run up migration twice
        run_sql_file(clean_db, up_sql)
        run_sql_file(clean_db, up_sql)  # Should not raise
        
        # Verify tables still exist
        with clean_db.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            count = cur.fetchone()[0]
            assert count >= 11, "Expected at least 11 tables"
    
    def test_down_migration_idempotent(self, clean_db: PgConnection) -> None:
        """Verify down migration can run multiple times without error."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        down_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.down.sql")
        
        # Setup
        run_sql_file(clean_db, up_sql)
        
        # Run down migration twice
        run_sql_file(clean_db, down_sql)
        run_sql_file(clean_db, down_sql)  # Should not raise
        
        # Verify tables are gone
        with clean_db.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name IN ('users', 'campaigns', 'contacts')
            """)
            count = cur.fetchone()[0]
            assert count == 0, "Tables should be dropped"


class TestMigrationRoundTrip:
    """Test migration round-trip (up -> down -> up)."""
    
    def test_round_trip(self, clean_db: PgConnection) -> None:
        """Verify up -> down -> up works correctly."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        down_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.down.sql")
        
        # Up
        run_sql_file(clean_db, up_sql)
        
        # Verify tables exist
        with clean_db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
            count_after_up = cur.fetchone()[0]
            assert count_after_up >= 11
        
        # Down
        run_sql_file(clean_db, down_sql)
        
        # Verify tables gone
        with clean_db.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                AND table_name IN ('users', 'campaigns', 'contacts')
            """)
            count_after_down = cur.fetchone()[0]
            assert count_after_down == 0
        
        # Up again
        run_sql_file(clean_db, up_sql)
        
        # Verify tables exist again
        with clean_db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
            count_after_up_again = cur.fetchone()[0]
            assert count_after_up_again >= 11


class TestSeedData:
    """Test seed data is idempotent and correct."""
    
    def test_seed_idempotent(self, clean_db: PgConnection) -> None:
        """Verify seed can run multiple times without error."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        seed_sql = os.path.join(script_dir, "src", "storage", "seed", "seed.sql")
        
        # Setup schema
        run_sql_file(clean_db, up_sql)
        
        # Run seed twice
        run_sql_file(clean_db, seed_sql)
        run_sql_file(clean_db, seed_sql)  # Should not raise
        
        # Verify expected counts (should not duplicate)
        with clean_db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            assert cur.fetchone()[0] == 3, "Expected 3 users"
            
            cur.execute("SELECT COUNT(*) FROM email_templates")
            assert cur.fetchone()[0] == 6, "Expected 6 email templates"
            
            cur.execute("SELECT COUNT(*) FROM provider_configs")
            assert cur.fetchone()[0] == 1, "Expected 1 provider config"
            
            cur.execute("SELECT COUNT(*) FROM campaigns")
            assert cur.fetchone()[0] == 1, "Expected 1 campaign"
            
            cur.execute("SELECT COUNT(*) FROM contacts")
            assert cur.fetchone()[0] == 5, "Expected 5 contacts"
            
            cur.execute("SELECT COUNT(*) FROM exclusion_list_entries")
            assert cur.fetchone()[0] == 2, "Expected 2 exclusion entries"
    
    def test_seed_data_correct(self, clean_db: PgConnection) -> None:
        """Verify seed data has correct values."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        seed_sql = os.path.join(script_dir, "src", "storage", "seed", "seed.sql")
        
        run_sql_file(clean_db, up_sql)
        run_sql_file(clean_db, seed_sql)
        
        with clean_db.cursor() as cur:
            # Check admin user
            cur.execute("SELECT role FROM users WHERE email = 'admin@voicesurvey.local'")
            result = cur.fetchone()
            assert result is not None
            assert result[0] == "admin"
            
            # Check campaign has correct questions
            cur.execute("SELECT question_1_type, question_2_type, question_3_type FROM campaigns LIMIT 1")
            result = cur.fetchone()
            assert result is not None
            assert result[0] == "scale"
            assert result[1] == "free_text"
            assert result[2] == "numeric"
            
            # Check excluded contact
            cur.execute("SELECT state FROM contacts WHERE do_not_call = true")
            result = cur.fetchone()
            assert result is not None
            assert result[0] == "excluded"


class TestConstraints:
    """Test database constraints are enforced."""
    
    def test_max_attempts_constraint(self, clean_db: PgConnection) -> None:
        """Verify max_attempts constraint (1-5)."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        seed_sql = os.path.join(script_dir, "src", "storage", "seed", "seed.sql")
        
        run_sql_file(clean_db, up_sql)
        run_sql_file(clean_db, seed_sql)
        
        with clean_db.cursor() as cur:
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
                        10, '00000000-0000-0000-0000-000000000001'
                    )
                """)
                clean_db.commit()
    
    def test_unique_constraints(self, clean_db: PgConnection) -> None:
        """Verify unique constraints are enforced."""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        up_sql = os.path.join(script_dir, "src", "storage", "sql", "V0001.up.sql")
        seed_sql = os.path.join(script_dir, "src", "storage", "seed", "seed.sql")
        
        run_sql_file(clean_db, up_sql)
        run_sql_file(clean_db, seed_sql)
        
        with clean_db.cursor() as cur:
            # Try to insert duplicate oidc_sub
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cur.execute("""
                    INSERT INTO users (oidc_sub, email, name, role)
                    VALUES ('admin-oidc-sub-001', 'different@email.com', 'Test', 'viewer')
                """)
                clean_db.commit()