#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${BACKUP_DIR:?BACKUP_DIR must be set in the env file}"

POSTGRES_USER="${POSTGRES_USER:-mooncare}"
POSTGRES_DB="${POSTGRES_DB:-mooncare}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_file="$BACKUP_DIR/mooncare-postgres-${timestamp}.sql.gz"

echo "Creating backup: $backup_file"
docker compose \
  --project-directory "$ROOT_DIR" \
  --env-file "$ENV_FILE" \
  exec -T postgres \
  pg_dump --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  | gzip -c > "$backup_file"

if [[ "$RETENTION_DAYS" =~ ^[0-9]+$ ]] && [[ "$RETENTION_DAYS" -gt 0 ]]; then
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'mooncare-postgres-*.sql.gz' -mtime +"$RETENTION_DAYS" -delete
fi

echo "Backup completed: $backup_file"
