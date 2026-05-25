#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$APP_DIR"

echo "MoonCARE deploy directory: $APP_DIR"

if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ] || [ ! -d "backend/app" ] || [ ! -f "frontend/dist/index.html" ]; then
    echo "ERROR: This directory is not a complete MoonCARE deployment package."
    echo "Expected docker-compose.yml, Dockerfile, backend/app, and frontend/dist/index.html."
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is not installed or not in PATH."
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: docker compose is not available."
    exit 1
fi

if [ ! -f ".env" ]; then
    cp .env.example .env
    chmod 600 .env || true
    echo "Created .env from .env.example."
    echo "Edit /www/wwwroot/MoonCARE/.env and replace DB_PASSWORD, SECRET_KEY, SMTP_*, and NVIDIA_API_KEY before deploying."
    exit 1
fi

if grep -Eq 'replace_with_|your_.*authorization_code|your_sender@163.com' .env; then
    echo "ERROR: .env still contains placeholder values. Replace them before deployment."
    grep -En 'replace_with_|your_.*authorization_code|your_sender@163.com' .env || true
    exit 1
fi

if ! grep -q '^RUN_DB_MIGRATIONS=' .env; then
    echo 'RUN_DB_MIGRATIONS=false' >> .env
elif grep -q '^RUN_DB_MIGRATIONS=true' .env; then
    echo "ERROR: RUN_DB_MIGRATIONS=true but this deployment is configured to use the existing database."
    echo "Set RUN_DB_MIGRATIONS=false unless you intentionally want Alembic migration."
    exit 1
fi

mkdir -p "${BACKUP_DIR:-/www/backup}" || true

echo "Validating Docker Compose config..."
docker compose config >/tmp/mooncare-compose-config.yml

echo "Stopping old MoonCARE containers without deleting volumes..."
docker compose down

if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    echo "FORCE_REBUILD=1; removing old mooncare:latest image if present..."
    docker image rm mooncare:latest >/dev/null 2>&1 || true
fi

echo "Building app image..."
docker compose build app

echo "Starting services..."
docker compose up -d

echo "Waiting for /health..."
for i in $(seq 1 60); do
    if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "MoonCARE health check passed."
        docker compose ps
        exit 0
    fi
    sleep 2
done

echo "ERROR: MoonCARE did not become healthy in time. Recent app logs:"
docker compose logs --tail=120 app
exit 1
