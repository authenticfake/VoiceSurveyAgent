#!/bin/bash
# Run all down migrations in reverse order

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="$SCRIPT_DIR/../src/storage/sql"

# Default database URL
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running rollback against: $DATABASE_URL"

# Run migrations in reverse order
for migration in $(ls "$SQL_DIR"/*.down.sql | sort -r); do
    echo "Rolling back: $(basename $migration)"
    psql "$DATABASE_URL" -f "$migration"
done

echo "All migrations rolled back successfully"