#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: bash scripts/db_import.sh <dump-file-path>"
  exit 1
fi

DUMP_FILE="$1"
if [ ! -f "$DUMP_FILE" ]; then
  echo "Dump file not found: $DUMP_FILE"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DB_USER="${POSTGRES_USER:-healthora_user}"
DB_NAME="${POSTGRES_DB:-healthora}"

echo "Ensuring postgres service is up..."
docker compose up -d postgres

echo "Waiting for postgres readiness..."
ready=0
for _ in {1..30}; do
  if docker compose exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "Postgres did not become ready in time"
  exit 1
fi

echo "Stopping app services to avoid active DB connections..."
docker compose stop backend frontend >/dev/null 2>&1 || true

if [[ "$DUMP_FILE" == *.sql ]]; then
  echo "Importing plain SQL dump into '$DB_NAME'..."
  docker compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME" < "$DUMP_FILE"
else
  echo "Importing custom-format dump into '$DB_NAME'..."
  docker compose exec -T postgres pg_restore -U "$DB_USER" -d "$DB_NAME" --clean --if-exists --no-owner --no-privileges < "$DUMP_FILE"
fi

echo "Database import complete. Starting application services..."
docker compose up -d backend frontend
echo "Done."
