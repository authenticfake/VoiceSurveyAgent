#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is not set" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SQL_DIR="${SCRIPT_DIR}/../src/storage/sql"

mapfile -t SQL_FILES < <(ls "${SQL_DIR}"/V*.down.sql | sort -r)

if [[ ${#SQL_FILES[@]} -eq 0 ]]; then
  echo "No downgrade files found in ${SQL_DIR}" >&2
  exit 0
fi

for file in "${SQL_FILES[@]}"; do
  echo "Reverting ${file}"
  psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 -f "${file}"
  version="$(basename "${file}" .down.sql)"
  up_file="${SQL_DIR}/${version}.up.sql"
  if [[ -f "${up_file}" ]]; then
    checksum="$(sha256sum "${up_file}" | awk '{print $1}')"
  else
    checksum="$(sha256sum "${file}" | awk '{print $1}')"
  fi
  psql "${DATABASE_URL}" -X -v ON_ERROR_STOP=1 <<SQL
UPDATE schema_migrations
SET status = 'rolled_back',
    checksum = 'sha256:${checksum}',
    applied_at = NOW()
WHERE version = '${version}';
SQL
done

echo "Migrations rolled back."