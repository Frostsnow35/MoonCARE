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

# 运行 Alembic 数据库迁移
cd /app/backend
if [ -d "migrations" ]; then
    echo "Running database migrations..."
    alembic upgrade head
else
    echo "No migrations folder found; skipping alembic upgrade."
fi

# 执行 CMD
exec "$@"