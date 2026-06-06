#!/bin/sh
set -e

# 等待数据库就绪（如果使用 PostgreSQL）
if [ -n "$DATABASE_URL" ]; then
    case "$DATABASE_URL" in
        postgresql*)
            echo "Waiting for PostgreSQL to be ready..."
            while ! pg_isready -d "$DATABASE_URL" -q; do
                sleep 1
            done
            echo "PostgreSQL is ready."
            ;;
    esac
fi

cd /app/backend

echo "Checking application import path..."
python -c "import app.main; print('Application import check passed.')"

# 默认不迁移数据库。生产部署沿用现有数据库/volume，只有明确设置 RUN_DB_MIGRATIONS=true 才执行 Alembic。
if [ "${RUN_DB_MIGRATIONS:-false}" = "true" ] && [ -d "migrations" ]; then
    echo "RUN_DB_MIGRATIONS=true; inspecting database schema state..."
    schema_action="$(python -m app.bootstrap_schema --print-action)"
    case "$schema_action" in
        migrate)
            echo "Alembic version table detected; running database migrations..."
            alembic upgrade head
            ;;
        bootstrap_fresh|adopt_existing)
            echo "Schema action is ${schema_action}; creating missing tables from metadata and stamping alembic head."
            python -m app.bootstrap_schema --apply-if-needed
            alembic stamp head
            ;;
        manual_intervention)
            echo "Existing database schema is partially managed but missing required columns."
            echo "Refusing to stamp head automatically. Inspect the schema and migrate manually before retrying."
            exit 1
            ;;
        *)
            echo "Unknown schema bootstrap action: ${schema_action}"
            exit 1
            ;;
    esac
elif [ "${RUN_DB_MIGRATIONS:-false}" = "true" ]; then
    echo "RUN_DB_MIGRATIONS=true but no migrations folder found; skipping alembic upgrade."
else
    echo "RUN_DB_MIGRATIONS is not true; skipping database migrations."
fi

# 执行 CMD
exec "$@"
