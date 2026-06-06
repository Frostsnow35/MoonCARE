#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  restore_postgres.sh <backup_file.sql.gz|backup_file.sql> [env_file] --yes

Notes:
  - This restores into the running postgres container defined by docker compose.
  - The dump is expected to be produced by backup_postgres.sh and includes --clean.
  - --yes is required because this operation overwrites application data.
EOF
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

BACKUP_FILE="$1"
ENV_FILE="$2"
CONFIRM_FLAG="${3:-}"

if [[ "$ENV_FILE" == "--yes" ]]; then
  ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.env"
  CONFIRM_FLAG="$2"
fi

if [[ "$CONFIRM_FLAG" != "--yes" ]]; then
  echo "Refusing to restore without --yes" >&2
  exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE" >&2
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

POSTGRES_USER="${POSTGRES_USER:-mooncare}"
POSTGRES_DB="${POSTGRES_DB:-mooncare}"

echo "Restoring $BACKUP_FILE into database '$POSTGRES_DB'..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
  gzip -dc -- "$BACKUP_FILE"
else
  cat -- "$BACKUP_FILE"
fi | docker compose \
  --project-directory "$ROOT_DIR" \
  --env-file "$ENV_FILE" \
  exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Restore completed."
