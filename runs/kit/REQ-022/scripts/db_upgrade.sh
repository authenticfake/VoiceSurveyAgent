#!/bin/bash
# db_upgrade.sh - Run all up migrations for REQ-022
# Usage: ./db_upgrade.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Check for DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set"
    exit 1
fi

echo "Running database migrations..."

# Run migrations in order
for migration in $(ls -1 "${SQL_DIR}"/*.up.sql 2>/dev/null | sort); do
    echo "Applying: $(basename "$migration")"
    psql "$DATABASE_URL" -f "$migration"
done

echo "Migrations completed successfully"