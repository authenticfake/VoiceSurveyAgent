#!/bin/bash
# db_upgrade.sh - Run all up migrations in order for REQ-019
# Usage: ./db_upgrade.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Database connection from environment or default
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running migrations from: ${SQL_DIR}"
echo "Database: ${DATABASE_URL}"

# Run migrations in order
for migration in $(ls -1 "${SQL_DIR}"/V*.up.sql 2>/dev/null | sort -V); do
    echo "Applying: $(basename ${migration})"
    psql "${DATABASE_URL}" -f "${migration}"
done

echo "All migrations applied successfully"