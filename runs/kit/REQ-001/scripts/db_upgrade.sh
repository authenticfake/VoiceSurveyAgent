#!/bin/bash
# db_upgrade.sh - Run all up migrations in order
# Usage: ./db_upgrade.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Load database URL from environment or use default
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running database migrations..."
echo "Database: ${DATABASE_URL%%@*}@***"

# Find and sort all .up.sql files
for migration in $(ls -1 "${SQL_DIR}"/*.up.sql 2>/dev/null | sort); do
    echo "Applying: $(basename "${migration}")"
    psql "${DATABASE_URL}" -f "${migration}" -v ON_ERROR_STOP=1
    echo "Applied: $(basename "${migration}")"
done

echo "All migrations applied successfully."