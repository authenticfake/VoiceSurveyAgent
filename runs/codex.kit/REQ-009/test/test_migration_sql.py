import os
from pathlib import Path

import psycopg
import pytest
import sqlparse

try:
    from testcontainers.postgres import PostgresContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:  # pragma: no cover
    TESTCONTAINERS_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
UP_SQL = ROOT / "src" / "storage" / "sql" / "V0001.up.sql"
DOWN_SQL = ROOT / "src" / "storage" / "sql" / "V0001.down.sql"


def execute_sql_file(connection: psycopg.Connection, path: Path) -> None:
    statements = [
        statement.strip()
        for statement in sqlparse.split(path.read_text())
        if statement.strip()
    ]
    for statement in statements:
        connection.execute(statement)


@pytest.fixture(scope="module")
def db_conn():
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        conn = psycopg.connect(url)
        conn.autocommit = True
        yield conn
        conn.close()
        return

    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("Testcontainers is unavailable and TEST_DATABASE_URL is not configured.")

    try:
        with PostgresContainer("postgres:16") as pg:
            conn = psycopg.connect(pg.get_connection_url())
            conn.autocommit = True
            try:
                yield conn
            finally:
                conn.close()
    except Exception as exc:
        pytest.skip(f"Could not start Postgres container: {exc!s}")


def table_exists(connection: psycopg.Connection, table: str) -> bool:
    query = "SELECT to_regclass(%s);"
    return connection.execute(query, (f"public.{table}",)).fetchone()[0] is not None


def test_migration_round_trip_is_idempotent(db_conn):
    execute_sql_file(db_conn, UP_SQL)
    assert table_exists(db_conn, "campaigns")
    assert table_exists(db_conn, "contacts")

    # idempotent re-run
    execute_sql_file(db_conn, UP_SQL)
    assert table_exists(db_conn, "schema_migrations")

    execute_sql_file(db_conn, DOWN_SQL)
    assert not table_exists(db_conn, "campaigns")
    assert table_exists(db_conn, "schema_migrations")