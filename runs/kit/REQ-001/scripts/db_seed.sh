#!/bin/bash
# db_seed.sh - Run seed data (idempotent)
# Usage: ./db_seed.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_DIR="${SCRIPT_DIR}/../src/storage/seed"

# Load database URL from environment or use default
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/voicesurvey}"

echo "Running database seed..."
echo "Database: ${DATABASE_URL%%@*}@***"

psql "${DATABASE_URL}" -f "${SEED_DIR}/seed.sql" -v ON_ERROR_STOP=1

echo "Seed data applied successfully."