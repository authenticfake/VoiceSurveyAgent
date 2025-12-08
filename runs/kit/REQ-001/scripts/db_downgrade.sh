#!/bin/bash
# db_downgrade.sh - Run all down migrations in reverse order
# Usage: ./db_downgrade.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Load database URL from environment or use default
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running database rollback..."
echo "Database: ${DATABASE_URL%%@*}@***"

# Find and reverse sort all .down.sql files
for migration in $(ls -1 "${SQL_DIR}"/*.down.sql 2>/dev/null | sort -r); do
    echo "Rolling back: $(basename "${migration}")"
    psql "${DATABASE_URL}" -f "${migration}" -v ON_ERROR_STOP=1
    echo "Rolled back: $(basename "${migration}")"
done

echo "All migrations rolled back successfully."