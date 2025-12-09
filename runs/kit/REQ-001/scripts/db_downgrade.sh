#!/usr/bin/env bash
# db_downgrade.sh - Run all *.down.sql migrations in reverse order
# Usage: ./db_downgrade.sh
# Requires: DATABASE_URL environment variable or defaults to local postgres

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

# Default DATABASE_URL for local development
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurveyagent}"

echo "=== Voice Survey Agent - Database Downgrade ==="
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

# Find and reverse sort all .down.sql files
DOWN_FILES=$(find "${SQL_DIR}" -name "*.down.sql" -type f | sort -r)

if [ -z "${DOWN_FILES}" ]; then
    echo "No downgrade files found."
    exit 0
fi

echo "Found downgrade files (will apply in reverse order):"
echo "${DOWN_FILES}" | while read -r file; do
    echo "  - $(basename "${file}")"
done
echo ""

# Confirm before proceeding
read -p "WARNING: This will drop all tables and data. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Run each downgrade
for file in ${DOWN_FILES}; do
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
echo "=== All downgrades applied successfully ==="