#!/bin/bash
# db_seed.sh - Run seed data script
# Usage: ./db_seed.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEED_FILE="${SCRIPT_DIR}/../src/storage/seed/seed.sql"

# Check for DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set"
    echo "Example: export DATABASE_URL='postgresql://user:password@localhost:5432/voicesurvey'"
    exit 1
fi

echo "Running seed data..."
psql "$DATABASE_URL" -f "$SEED_FILE"
echo "Seed data applied successfully."