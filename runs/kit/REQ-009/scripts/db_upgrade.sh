#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

mapfile -t SQL_FILES < <(ls "${SQL_DIR}"/V*.up.sql | sort)

if [[ ${#SQL_FILES[@]} -eq 0 ]]; then
  echo "No migration files found in ${SQL_DIR}" >&2
  exit 0
fi

for file in "${SQL_FILES[@]}"; do
  echo "Applying ${file}"
  psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -f "${file}"
  version="$(basename "${file}" .up.sql)"
  checksum="$(sha256sum "${file}" | awk '{print $1}')"
  psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 <<SQL
INSERT INTO schema_migrations (version, checksum, status)
VALUES ('${version}', 'sha256:${checksum}', 'applied')
ON CONFLICT (version) DO UPDATE
SET checksum = EXCLUDED.checksum,
    status = 'applied',
    applied_at = NOW();
SQL
done

echo "Migrations applied successfully."