#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$APP_DIR"

echo "MoonCARE deploy directory: $APP_DIR"

generate_secret() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 32
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
    else
        date +%s%N | sha256sum | awk '{print $1}'
    fi
}

set_env_value() {
    key="$1"
    value="$2"
    tmp_file=".env.tmp.$$"
    awk -v key="$key" -v value="$value" '
        BEGIN { found = 0 }
        $0 ~ "^" key "=" {
            print key "=" value
            found = 1
            next
        }
        { print }
        END {
            if (!found) {
                print key "=" value
            }
        }
    ' .env > "$tmp_file"
    mv "$tmp_file" .env
}

get_existing_db_password() {
    if docker inspect mooncare-postgres >/dev/null 2>&1; then
        docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' mooncare-postgres \
            | awk -F= '$1 == "POSTGRES_PASSWORD" {print substr($0, index($0, "=") + 1)}' \
            | tail -n 1
    fi
}

append_env_default() {
    key="$1"
    value="$2"
    if grep -q "^${key}=" .env; then
        return 0
    else
        printf '%s=%s\n' "$key" "$value" >> .env
    fi
}

if [ ! -f "docker-compose.yml" ] || [ ! -f "Dockerfile" ] || [ ! -d "backend/app" ] || [ ! -f "frontend/package.json" ] || [ ! -d "frontend/src" ]; then
    echo "ERROR: This directory is not a complete MoonCARE deployment package."
    echo "Expected docker-compose.yml, Dockerfile, backend/app, frontend/package.json, and frontend/src."
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
fi

if grep -Eiq '^DB_PASSWORD=$|^DB_PASSWORD=REPLACE_WITH_|^DB_PASSWORD=replace_with_' .env; then
    EXISTING_DB_PASSWORD="$(get_existing_db_password || true)"
    if [ -n "$EXISTING_DB_PASSWORD" ]; then
        set_env_value DB_PASSWORD "$EXISTING_DB_PASSWORD"
        echo "Reused DB_PASSWORD from existing mooncare-postgres container."
    else
        set_env_value DB_PASSWORD "$(generate_secret)"
        echo "Generated DB_PASSWORD in .env."
    fi
fi

if grep -Eiq '^SECRET_KEY=$|^SECRET_KEY=REPLACE_WITH_|^SECRET_KEY=replace_with_' .env; then
    set_env_value SECRET_KEY "$(generate_secret)"
    echo "Generated SECRET_KEY in .env."
fi

# Optional integrations must not block database/app readiness. Keep them empty
# until SMTP and provider keys are available on the server. Placeholder values
# are cleared instead of being deployed as literal strings.
if grep -Eiq '^SMTP_HOST=REPLACE_WITH_|^SMTP_HOST=replace_with_' .env; then set_env_value SMTP_HOST ""; fi
if grep -Eiq '^SMTP_USERNAME=REPLACE_WITH_|^SMTP_USERNAME=replace_with_' .env; then set_env_value SMTP_USERNAME ""; fi
if grep -Eiq '^SMTP_PASSWORD=REPLACE_WITH_|^SMTP_PASSWORD=replace_with_' .env; then set_env_value SMTP_PASSWORD ""; fi
if grep -Eiq '^SMTP_FROM_EMAIL=REPLACE_WITH_|^SMTP_FROM_EMAIL=replace_with_' .env; then set_env_value SMTP_FROM_EMAIL ""; fi
if grep -Eiq '^NVIDIA_API_KEY=REPLACE_WITH_|^NVIDIA_API_KEY=replace_with_' .env; then set_env_value NVIDIA_API_KEY ""; fi

if ! grep -q '^RUN_DB_MIGRATIONS=' .env; then
    echo 'RUN_DB_MIGRATIONS=false' >> .env
elif grep -q '^RUN_DB_MIGRATIONS=true' .env; then
    echo "RUN_DB_MIGRATIONS=true; Alembic migrations will run during app startup."
fi

append_env_default APP_PORT 18000
append_env_default POSTGRES_PORT 15432
append_env_default POSTGRES_READY_TIMEOUT_SECONDS 90
append_env_default PIP_INDEX_URL https://pypi.tuna.tsinghua.edu.cn/simple
append_env_default PIP_TRUSTED_HOST pypi.tuna.tsinghua.edu.cn
append_env_default PIP_DEFAULT_TIMEOUT 300
append_env_default PIP_RETRIES 10

mkdir -p "${BACKUP_DIR:-/www/backup}" || true

APP_PORT_VALUE="$(grep -E '^APP_PORT=' .env | tail -n 1 | cut -d= -f2- || true)"
APP_PORT_VALUE="${APP_PORT_VALUE:-18000}"
POSTGRES_PORT_VALUE="$(grep -E '^POSTGRES_PORT=' .env | tail -n 1 | cut -d= -f2- || true)"
POSTGRES_PORT_VALUE="${POSTGRES_PORT_VALUE:-15432}"

echo "Using host ports: app=${APP_PORT_VALUE}, postgres=${POSTGRES_PORT_VALUE}"

echo "Validating Docker Compose config..."
docker compose config >/tmp/mooncare-compose-config.yml

echo "Stopping old MoonCARE containers without deleting volumes..."
docker compose down

if command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${APP_PORT_VALUE}$"; then
        echo "ERROR: APP_PORT=${APP_PORT_VALUE} is already listening on this host after stopping MoonCARE."
        echo "Edit .env and choose another APP_PORT, then update Nginx upstream to the same port."
        exit 1
    fi
    if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${POSTGRES_PORT_VALUE}$"; then
        echo "ERROR: POSTGRES_PORT=${POSTGRES_PORT_VALUE} is already listening on this host after stopping MoonCARE."
        echo "Edit .env and choose another POSTGRES_PORT, or remove the postgres port mapping if not needed."
        exit 1
    fi
fi

if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    echo "FORCE_REBUILD=1; removing old mooncare:latest image if present..."
    docker image rm mooncare:latest >/dev/null 2>&1 || true
fi

echo "Building app image..."
if [ "${FORCE_REBUILD:-0}" = "1" ]; then
    docker compose build --no-cache app
else
    docker compose build app
fi

echo "Verifying app image imports..."
docker compose run --rm --entrypoint sh app -lc 'cd /app/backend && python -c "from app.models.music import Music, MusicFeedback; import app.main; print(\"Image import check passed.\")"'

echo "Starting PostgreSQL service..."
docker compose up -d postgres

echo "Waiting for PostgreSQL to become ready..."
for i in $(seq 1 60); do
    if docker compose exec -T postgres pg_isready -U mooncare -d mooncare >/dev/null 2>&1; then
        echo "PostgreSQL is ready for connections."
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "ERROR: PostgreSQL did not become ready in time. Recent postgres logs:"
        docker compose logs --tail=120 postgres
        exit 1
    fi
    sleep 2
done

echo "Starting app service..."
docker compose up -d app

echo "Waiting for /health..."
for i in $(seq 1 60); do
    if curl -fsS "http://127.0.0.1:${APP_PORT_VALUE}/health" >/dev/null 2>&1; then
        echo "MoonCARE health check passed."
        docker compose ps
        exit 0
    fi
    sleep 2
done

echo "ERROR: MoonCARE did not become healthy in time. Recent app logs:"
docker compose logs --tail=120 app
exit 1
