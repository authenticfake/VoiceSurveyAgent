"""
Tests for database migrations.

REQ-018: Campaign CSV export
"""

import os

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


SKIP_DB_TESTS = os.environ.get("SKIP_DB_TESTS", "0") == "1"
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/voicesurvey_test",
)


@pytest.fixture(scope="module")
def migration_sql_dir():
    """Get path to SQL migration files."""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "src",
        "storage",
        "sql",
    )


class TestMigrationV0002:
    """Tests for V0002 migration (export_jobs table)."""

    @pytest_asyncio.fixture
    async def db_engine(self):
        """Create test database engine."""
        if SKIP_DB_TESTS:
            pytest.skip("Database tests skipped (SKIP_DB_TESTS=1)")

        engine = create_async_engine(DATABASE_URL, echo=False)
        yield engine
        await engine.dispose()

    @pytest_asyncio.fixture
    async def db_session(self, db_engine) -> AsyncSession:
        """Create test database session."""
        async_session = async_sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session

    @pytest.mark.asyncio
    async def test_migration_up_creates_table(
        self,
        db_session: AsyncSession,
        migration_sql_dir: str,
    ):
        """Test V0002.up.sql creates export_jobs table."""
        # Read and execute migration
        up_sql_path = os.path.join(migration_sql_dir, "V0002.up.sql")
        with open(up_sql_path) as f:
            up_sql = f.read()

        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Verify table exists
        result = await db_session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'export_jobs'
                )
            """)
        )
        exists = result.scalar()
        assert exists is True

        # Verify columns
        result = await db_session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'export_jobs'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0]: (row[1], row[2]) for row in result.fetchall()}

        assert "id" in columns
        assert "campaign_id" in columns
        assert "status" in columns
        assert "s3_key" in columns
        assert "download_url" in columns
        assert "url_expires_at" in columns
        assert "total_records" in columns
        assert "error_message" in columns

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(
        self,
        db_session: AsyncSession,
        migration_sql_dir: str,
    ):
        """Test V0002.up.sql can be run multiple times."""
        up_sql_path = os.path.join(migration_sql_dir, "V0002.up.sql")
        with open(up_sql_path) as f:
            up_sql = f.read()

        # Run twice - should not error
        await db_session.execute(text(up_sql))
        await db_session.commit()

        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Verify table still exists
        result = await db_session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'export_jobs'
                )
            """)
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_migration_down_removes_table(
        self,
        db_session: AsyncSession,
        migration_sql_dir: str,
    ):
        """Test V0002.down.sql removes export_jobs table."""
        # First apply up migration
        up_sql_path = os.path.join(migration_sql_dir, "V0002.up.sql")
        with open(up_sql_path) as f:
            up_sql = f.read()
        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Then apply down migration
        down_sql_path = os.path.join(migration_sql_dir, "V0002.down.sql")
        with open(down_sql_path) as f:
            down_sql = f.read()
        await db_session.execute(text(down_sql))
        await db_session.commit()

        # Verify table is gone
        result = await db_session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'export_jobs'
                )
            """)
        )
        exists = result.scalar()
        assert exists is False

    @pytest.mark.asyncio
    async def test_migration_roundtrip(
        self,
        db_session: AsyncSession,
        migration_sql_dir: str,
    ):
        """Test up -> down -> up migration cycle."""
        up_sql_path = os.path.join(migration_sql_dir, "V0002.up.sql")
        down_sql_path = os.path.join(migration_sql_dir, "V0002.down.sql")

        with open(up_sql_path) as f:
            up_sql = f.read()
        with open(down_sql_path) as f:
            down_sql = f.read()

        # Up
        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Down
        await db_session.execute(text(down_sql))
        await db_session.commit()

        # Up again
        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Verify table exists
        result = await db_session.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'export_jobs'
                )
            """)
        )
        exists = result.scalar()
        assert exists is True

    @pytest.mark.asyncio
    async def test_export_job_status_enum(
        self,
        db_session: AsyncSession,
        migration_sql_dir: str,
    ):
        """Test export_job_status enum is created correctly."""
        up_sql_path = os.path.join(migration_sql_dir, "V0002.up.sql")
        with open(up_sql_path) as f:
            up_sql = f.read()
        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Verify enum values
        result = await db_session.execute(
            text("""
                SELECT enumlabel 
                FROM pg_enum 
                WHERE enumtypid = 'export_job_status'::regtype
                ORDER BY enumsortorder
            """)
        )
        values = [row[0] for row in result.fetchall()]

        assert "pending" in values
        assert "processing" in values
        assert "completed" in values
        assert "failed" in values

    @pytest.mark.asyncio
    async def test_indexes_created(
        self,
        db_session: AsyncSession,
        migration_sql_dir: str,
    ):
        """Test indexes are created on export_jobs table."""
        up_sql_path = os.path.join(migration_sql_dir, "V0002.up.sql")
        with open(up_sql_path) as f:
            up_sql = f.read()
        await db_session.execute(text(up_sql))
        await db_session.commit()

        # Verify indexes
        result = await db_session.execute(
            text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'export_jobs'
            """)
        )
        indexes = [row[0] for row in result.fetchall()]

        assert "ix_export_jobs_campaign_id" in indexes
        assert "ix_export_jobs_status" in indexes
        assert "ix_export_jobs_created_at" in indexes