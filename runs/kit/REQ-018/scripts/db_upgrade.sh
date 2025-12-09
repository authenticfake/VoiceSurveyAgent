#!/bin/bash
# Run all up migrations in order

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="$SCRIPT_DIR/../src/storage/sql"

# Default database URL
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running migrations against: $DATABASE_URL"

# Run migrations in order
for migration in $(ls "$SQL_DIR"/*.up.sql | sort); do
    echo "Applying: $(basename $migration)"
    psql "$DATABASE_URL" -f "$migration"
done

echo "All migrations applied successfully"