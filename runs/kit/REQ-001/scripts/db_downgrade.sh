#!/bin/bash
# db_downgrade.sh - Run all down migrations in reverse order
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="$SCRIPT_DIR/../src/storage/sql"

# Database connection from environment or defaults
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-voicesurveyagent}"
DB_USER="${DB_USER:-postgres}"

echo "Running database downgrade migrations..."
echo "Target database: $DB_NAME on $DB_HOST:$DB_PORT"

# Find and run all .down.sql files in reverse order
for migration in $(ls -1 "$SQL_DIR"/*.down.sql 2>/dev/null | sort -r); do
    echo "Reverting migration: $(basename "$migration")"
    PGPASSWORD="${DB_PASSWORD:-postgres}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration"
    echo "Migration $(basename "$migration") reverted successfully"
done

echo "All migrations reverted successfully"