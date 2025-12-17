#!/usr/bin/env bash
# db_seed.sh - Run seed data script
# Usage: ./db_seed.sh
# Requires: DATABASE_URL environment variable or defaults to local postgres

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="${SCRIPT_DIR}/../src/storage/seed/seed.sql"

# Default DATABASE_URL for local development
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurveyagent}"

echo "=== Voice Survey Agent - Database Seed ==="
echo "Target: ${DATABASE_URL%%@*}@***"
echo "Seed File: ${SEED_FILE}"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "ERROR: psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Check if seed file exists
if [ ! -f "${SEED_FILE}" ]; then
    echo "ERROR: Seed file not found: ${SEED_FILE}"
    exit 1
fi

echo "Applying seed data..."

if psql "${DATABASE_URL}" -f "${SEED_FILE}" -v ON_ERROR_STOP=1; then
    echo "  ✓ Seed data applied successfully"
else
    echo "  ✗ Seed data failed"
    exit 1
fi

echo ""
echo "=== Seed data applied successfully ==="