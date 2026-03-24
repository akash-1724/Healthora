#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUT_DIR="${1:-$ROOT_DIR/backups}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
OUT_FILE="${2:-$OUT_DIR/healthora_${TIMESTAMP}.dump}"

mkdir -p "$OUT_DIR"

DB_USER="${POSTGRES_USER:-healthora_user}"
DB_NAME="${POSTGRES_DB:-healthora}"

echo "Exporting database '$DB_NAME' from docker service 'postgres'..."
docker compose exec -T postgres pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc > "$OUT_FILE"
echo "Database export created: $OUT_FILE"
