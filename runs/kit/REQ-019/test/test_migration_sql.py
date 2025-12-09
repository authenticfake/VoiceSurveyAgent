"""
Migration tests for REQ-019: Admin configuration API
"""

import os
import pytest
from pathlib import Path

# Check if we can run database tests
try:
    import asyncpg
    import sqlalchemy
    HAS_DB_DEPS = True
except ImportError:
    HAS_DB_DEPS = False

# Check for database URL
DATABASE_URL = os.environ.get("DATABASE_URL", "")
HAS_DATABASE = bool(DATABASE_URL) and DATABASE_URL.startswith("postgresql")


@pytest.mark.skipif(not HAS_DB_DEPS, reason="Database dependencies not installed")
@pytest.mark.skipif(not HAS_DATABASE, reason="DATABASE_URL not configured")
class TestMigrations:
    """Tests for SQL migrations."""

    def test_migration_files_exist(self):
        """Test that migration files exist."""
        sql_dir = Path(__file__).parent.parent / "src" / "storage" / "sql"

        up_file = sql_dir / "V0003.up.sql"
        down_file = sql_dir / "V0003.down.sql"

        assert up_file.exists(), f"Up migration not found: {up_file}"
        assert down_file.exists(), f"Down migration not found: {down_file}"

    def test_migration_syntax(self):
        """Test that migration files have valid SQL syntax markers."""
        sql_dir = Path(__file__).parent.parent / "src" / "storage" / "sql"

        up_file = sql_dir / "V0003.up.sql"
        down_file = sql_dir / "V0003.down.sql"

        up_content = up_file.read_text()
        down_content = down_file.read_text()

        # Check for expected content in up migration
        assert "CREATE TABLE IF NOT EXISTS email_configs" in up_content
        assert "CREATE TABLE IF NOT EXISTS audit_logs" in up_content
        assert "CREATE INDEX IF NOT EXISTS" in up_content

        # Check for expected content in down migration
        assert "DROP TABLE IF EXISTS audit_logs" in down_content
        assert "DROP TABLE IF EXISTS email_configs" in down_content

    def test_seed_file_exists(self):
        """Test that seed file exists."""
        seed_file = Path(__file__).parent.parent / "src" / "storage" / "seed" / "seed.sql"

        assert seed_file.exists(), f"Seed file not found: {seed_file}"

    def test_seed_file_is_idempotent(self):
        """Test that seed file uses ON CONFLICT for idempotency."""
        seed_file = Path(__file__).parent.parent / "src" / "storage" / "seed" / "seed.sql"

        content = seed_file.read_text()

        # Check for idempotent inserts
        assert "ON CONFLICT" in content, "Seed file should use ON CONFLICT for idempotency"


class TestMigrationFilesStructure:
    """Tests for migration file structure (no database required)."""

    def test_up_migration_has_required_tables(self):
        """Test that up migration creates required tables."""
        sql_dir = Path(__file__).parent.parent / "src" / "storage" / "sql"
        up_file = sql_dir / "V0003.up.sql"

        content = up_file.read_text()

        # Required tables for REQ-019
        assert "email_configs" in content
        assert "audit_logs" in content

    def test_down_migration_drops_tables(self):
        """Test that down migration drops created tables."""
        sql_dir = Path(__file__).parent.parent / "src" / "storage" / "sql"
        down_file = sql_dir / "V0003.down.sql"

        content = down_file.read_text()

        # Should drop tables created in up migration
        assert "DROP TABLE IF EXISTS audit_logs" in content
        assert "DROP TABLE IF EXISTS email_configs" in content

    def test_migrations_are_idempotent(self):
        """Test that migrations use IF EXISTS/IF NOT EXISTS."""
        sql_dir = Path(__file__).parent.parent / "src" / "storage" / "sql"

        up_file = sql_dir / "V0003.up.sql"
        down_file = sql_dir / "V0003.down.sql"

        up_content = up_file.read_text()
        down_content = down_file.read_text()

        # Up migration should use IF NOT EXISTS
        assert "IF NOT EXISTS" in up_content

        # Down migration should use IF EXISTS
        assert "IF EXISTS" in down_content