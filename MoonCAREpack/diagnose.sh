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
test -f frontend/dist/index.html && echo "frontend/dist/index.html: ok" || echo "frontend/dist/index.html: missing"

echo "== Compose config =="
docker compose config >/tmp/mooncare-compose-config.yml
grep -E 'RUN_DB_MIGRATIONS|LLM_PROVIDER|NVIDIA_MODEL_NAME|DATABASE_URL|health' /tmp/mooncare-compose-config.yml || true

echo "== Containers =="
docker compose ps || true

echo "== App import inside image =="
docker compose run --rm --entrypoint sh app -lc 'pwd; ls -la /app/backend/app; cd /app/backend; python -c "import sys; print(sys.path); import app.main; print(app.main.app.title)"' || true

echo "== Health =="
curl -fsS http://127.0.0.1:8000/health || true
echo
curl -fsS http://127.0.0.1:8000/healthz || true
echo

echo "== Recent app logs =="
docker compose logs --tail=160 app || true

echo "== Recent postgres logs =="
docker compose logs --tail=80 postgres || true
