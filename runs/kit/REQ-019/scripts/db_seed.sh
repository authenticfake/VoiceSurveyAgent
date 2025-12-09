#!/bin/bash
# db_seed.sh - Run seed data for REQ-019
# Usage: ./db_seed.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="${SCRIPT_DIR}/../src/storage/seed/seed.sql"

# Database connection from environment or default
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running seed data from: ${SEED_FILE}"
echo "Database: ${DATABASE_URL}"

psql "${DATABASE_URL}" -f "${SEED_FILE}"

echo "Seed data applied successfully"