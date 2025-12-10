#!/bin/bash
# db_downgrade.sh - Run all down migrations for REQ-022 in reverse order
# Usage: ./db_downgrade.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Check for DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set"
    exit 1
fi

echo "Running database rollback..."

# Run down migrations in reverse order
for migration in $(ls -1 "${SQL_DIR}"/*.down.sql 2>/dev/null | sort -r); do
    echo "Rolling back: $(basename "$migration")"
    psql "$DATABASE_URL" -f "$migration"
done

echo "Rollback completed successfully"