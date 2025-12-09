#!/bin/bash
# db_downgrade.sh - Run all down migrations in reverse order for REQ-019
# Usage: ./db_downgrade.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Database connection from environment or default
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running rollback migrations from: ${SQL_DIR}"
echo "Database: ${DATABASE_URL}"

# Run down migrations in reverse order
for migration in $(ls -1 "${SQL_DIR}"/V*.down.sql 2>/dev/null | sort -rV); do
    echo "Rolling back: $(basename ${migration})"
    psql "${DATABASE_URL}" -f "${migration}"
done

echo "All rollback migrations applied successfully"