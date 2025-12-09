#!/usr/bin/env bash
# db_upgrade.sh - Run all *.up.sql migrations in order
# Usage: ./db_upgrade.sh
# Requires: DATABASE_URL environment variable or defaults to local postgres

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Default DATABASE_URL for local development
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurveyagent}"

echo "=== Voice Survey Agent - Database Upgrade ==="
echo "Target: ${DATABASE_URL%%@*}@***"
echo "SQL Directory: ${SQL_DIR}"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Check if SQL directory exists
if [ ! -d "${SQL_DIR}" ]; then
    echo "ERROR: SQL directory not found: ${SQL_DIR}"
    exit 1
fi

# Find and sort all .up.sql files
UP_FILES=$(find "${SQL_DIR}" -name "*.up.sql" -type f | sort)

if [ -z "${UP_FILES}" ]; then
    echo "No migration files found."
    exit 0
fi

echo "Found migration files:"
echo "${UP_FILES}" | while read -r file; do
    echo "  - $(basename "${file}")"
done
echo ""

# Run each migration
for file in ${UP_FILES}; do
    filename=$(basename "${file}")
    echo "Applying: ${filename}..."
    
    if psql "${DATABASE_URL}" -f "${file}" -v ON_ERROR_STOP=1; then
        echo "  ✓ ${filename} applied successfully"
    else
        echo "  ✗ ${filename} failed"
        exit 1
    fi
done

echo ""
echo "=== All migrations applied successfully ==="