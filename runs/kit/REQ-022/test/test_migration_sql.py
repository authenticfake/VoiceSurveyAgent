"""
Database migration tests for REQ-022.

REQ-022: Data retention jobs

Tests:
- Schema shape validation
- Migration idempotency
- Round-trip (up/down) migrations
"""

import os
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

# Skip if no database available
pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set - skipping database tests"
)


@pytest.fixture
def db_url():
    """Get database URL from environment."""
    return os.environ.get("DATABASE_URL")


class TestMigrationShape:
    """Tests for migration schema shape."""
    
    @pytest.mark.asyncio
    async def test_gdpr_deletion_requests_table_exists(self, db_url):
        """Test that gdpr_deletion_requests table is created."""
        import asyncpg
        
        conn = await asyncpg.connect(db_url)
        try:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'gdpr_deletion_requests'
                )
            """)
            assert result is True
        finally:
            await conn.close()
    
    @pytest.mark.asyncio
    async def test_retention_job_history_table_exists(self, db_url):
        """Test that retention_job_history table is created."""
        import asyncpg
        
        conn = await asyncpg.connect(db_url)
        try:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'retention_job_history'
                )
            """)
            assert result is True
        finally:
            await conn.close()
    
    @pytest.mark.asyncio
    async def test_gdpr_request_status_enum_exists(self, db_url):
        """Test that gdpr_request_status enum type exists."""
        import asyncpg
        
        conn = await asyncpg.connect(db_url)
        try:
            result = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM pg_type 
                    WHERE typname = 'gdpr_request_status'
                )
            """)
            assert result is True
        finally:
            await conn.close()
    
    @pytest.mark.asyncio
    async def test_gdpr_requests_columns(self, db_url):
        """Test gdpr_deletion_requests has required columns."""
        import asyncpg
        
        conn = await asyncpg.connect(db_url)
        try:
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'gdpr_deletion_requests'
            """)
            
            column_names = {c["column_name"] for c in columns}
            required = {
                "id", "contact_id", "contact_phone", "contact_email",
                "requested_at", "deadline", "status", "processed_at",
                "items_deleted", "error_message"
            }
            
            assert required.issubset(column_names)
        finally:
            await conn.close()
    
    @pytest.mark.asyncio
    async def test_retention_job_history_columns(self, db_url):
        """Test retention_job_history has required columns."""
        import asyncpg
        
        conn = await asyncpg.connect(db_url)
        try:
            columns = await conn.fetch("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'retention_job_history'
            """)
            
            column_names = {c["column_name"] for c in columns}
            required = {
                "id", "started_at", "completed_at", "status",
                "recordings_deleted", "recordings_failed",
                "transcripts_deleted", "transcripts_failed",
                "total_deleted", "total_failed", "error_message"
            }
            
            assert required.issubset(column_names)
        finally:
            await conn.close()


class TestMigrationIdempotency:
    """Tests for migration idempotency."""
    
    @pytest.mark.asyncio
    async def test_can_run_up_migration_twice(self, db_url):
        """Test that up migration can be run multiple times."""
        import asyncpg
        import subprocess
        
        # Run migration twice
        script_dir = os.path.dirname(os.path.dirname(__file__))
        sql_file = os.path.join(script_dir, "src/storage/sql/V0004.up.sql")
        
        if os.path.exists(sql_file):
            # First run
            result1 = subprocess.run(
                ["psql", db_url, "-f", sql_file],
                capture_output=True,
                text=True
            )
            
            # Second run should not fail
            result2 = subprocess.run(
                ["psql", db_url, "-f", sql_file],
                capture_output=True,
                text=True
            )
            
            assert result2.returncode == 0


class TestMigrationRoundTrip:
    """Tests for migration round-trip (up/down)."""
    
    @pytest.mark.asyncio
    async def test_up_down_up_cycle(self, db_url):
        """Test that migrations can be applied, rolled back, and reapplied."""
        import subprocess
        
        script_dir = os.path.dirname(os.path.dirname(__file__))
        up_file = os.path.join(script_dir, "src/storage/sql/V0004.up.sql")
        down_file = os.path.join(script_dir, "src/storage/sql/V0004.down.sql")
        
        if os.path.exists(up_file) and os.path.exists(down_file):
            # Up
            result = subprocess.run(
                ["psql", db_url, "-f", up_file],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            
            # Down
            result = subprocess.run(
                ["psql", db_url, "-f", down_file],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0
            
            # Up again
            result = subprocess.run(
                ["psql", db_url, "-f", up_file],
                capture_output=True,
                text=True
            )
            assert result.returncode == 0