#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$APP_DIR"

echo "== MoonCARE package =="
pwd
ls -la

echo "== Required files =="
test -f Dockerfile && echo "Dockerfile: ok" || echo "Dockerfile: missing"
test -f docker-compose.yml && echo "docker-compose.yml: ok" || echo "docker-compose.yml: missing"
test -f .env && echo ".env: ok" || echo ".env: missing"
test -d backend/app && echo "backend/app: ok" || echo "backend/app: missing"
test -f frontend/package.json && echo "frontend/package.json: ok" || echo "frontend/package.json: missing"
test -d frontend/src && echo "frontend/src: ok" || echo "frontend/src: missing"

echo "== Compose config =="
docker compose config >/tmp/mooncare-compose-config.yml
grep -E 'APP_PORT|POSTGRES_PORT|PIP_INDEX_URL|PIP_DEFAULT_TIMEOUT|RUN_DB_MIGRATIONS|LLM_PROVIDER|NVIDIA_MODEL_NAME|DATABASE_URL|health|published' /tmp/mooncare-compose-config.yml || true

echo "== Containers =="
docker compose ps || true

echo "== PostgreSQL readiness =="
docker compose exec -T postgres pg_isready -U mooncare -d mooncare || true
docker volume ls | grep -E 'mooncare.*postgres|postgres_data' || true

echo "== App import inside image =="
docker compose run --rm --entrypoint sh app -lc 'pwd; ls -la /app/backend/app; cd /app/backend; python -c "import sys; print(sys.path); import app.main; print(app.main.app.title)"' || true

echo "== Health =="
APP_PORT_VALUE="$(grep -E '^APP_PORT=' .env 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
APP_PORT_VALUE="${APP_PORT_VALUE:-18000}"
curl -fsS "http://127.0.0.1:${APP_PORT_VALUE}/health" || true
echo
curl -fsS "http://127.0.0.1:${APP_PORT_VALUE}/healthz" || true
echo

echo "== Recent app logs =="
docker compose logs --tail=160 app || true

echo "== Recent postgres logs =="
docker compose logs --tail=80 postgres || true
