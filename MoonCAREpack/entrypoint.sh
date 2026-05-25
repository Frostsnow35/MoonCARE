#!/bin/sh
set -e

# Wait for PostgreSQL when DATABASE_URL points to the compose database.
if [ -n "$DATABASE_URL" ]; then
    case "$DATABASE_URL" in
        postgresql*)
            echo "Waiting for PostgreSQL to be ready..."
            DB_READY_HOST="${POSTGRES_HOST:-postgres}"
            DB_READY_PORT="${POSTGRES_PORT_INTERNAL:-5432}"
            DB_READY_USER="${POSTGRES_USER:-mooncare}"
            DB_READY_NAME="${POSTGRES_DB:-mooncare}"
            DB_READY_TIMEOUT="${POSTGRES_READY_TIMEOUT_SECONDS:-90}"
            elapsed=0

            while ! pg_isready -h "$DB_READY_HOST" -p "$DB_READY_PORT" -U "$DB_READY_USER" -d "$DB_READY_NAME" -q; do
                elapsed=$((elapsed + 1))
                if [ "$elapsed" -ge "$DB_READY_TIMEOUT" ]; then
                    echo "ERROR: PostgreSQL was not ready after ${DB_READY_TIMEOUT}s."
                    echo "Checked host=${DB_READY_HOST} port=${DB_READY_PORT} user=${DB_READY_USER} db=${DB_READY_NAME}."
                    exit 1
                fi
                sleep 1
            done
            echo "PostgreSQL is ready."
            ;;
    esac
fi

cd /app/backend

echo "Checking application import path..."
python -c "import app.main; print('Application import check passed.')"

# Do not run Alembic by default. Server deployment keeps the existing database/volume
# unless RUN_DB_MIGRATIONS=true is set deliberately.
if [ "${RUN_DB_MIGRATIONS:-false}" = "true" ] && [ -d "migrations" ]; then
    echo "RUN_DB_MIGRATIONS=true; running database migrations..."
    alembic upgrade head
elif [ "${RUN_DB_MIGRATIONS:-false}" = "true" ]; then
    echo "RUN_DB_MIGRATIONS=true but no migrations folder found; skipping alembic upgrade."
else
    echo "RUN_DB_MIGRATIONS is not true; skipping database migrations."
fi

exec "$@"
