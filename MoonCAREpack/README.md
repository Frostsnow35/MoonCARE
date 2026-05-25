# MoonCAREpack

MoonCAREpack is the Docker-first handoff package for running MoonCARE from a cloned Git branch or from `/www/wwwroot/MoonCARE` on a server.

## Quick Start

Prerequisites:

- Docker Engine
- Docker Compose v2 (`docker compose version`)
- Network access for pulling `python:3.11-slim` and `postgres:15-alpine`

Run:

```bash
cd MoonCAREpack
bash deploy.sh
```

The script will:

- create `.env` from `.env.example` if missing
- generate `DB_PASSWORD` and `SECRET_KEY` when they are still placeholders
- keep `RUN_DB_MIGRATIONS=false`
- start PostgreSQL first and wait for `pg_isready`
- build the app image
- verify `app.main` imports inside the image before starting the app
- wait for `http://127.0.0.1:18000/health`

Open locally:

```text
http://127.0.0.1:18000
```

## Useful Commands

```bash
cd MoonCAREpack
docker compose ps
curl -fsS http://127.0.0.1:18000/health
bash diagnose.sh
```

Force a clean rebuild after code changes:

```bash
cd MoonCAREpack
FORCE_REBUILD=1 bash deploy.sh
```

## Server Layout

For the current server workflow, place the package at:

```text
/www/wwwroot/MoonCARE
```

The default ports bind to localhost:

```text
app:      127.0.0.1:18000 -> container 8000
postgres: 127.0.0.1:15432 -> container 5432
```

Use `deploy/nginx/mooncare-ip.conf` for Nginx 1.28.3 IP access while the public network remains closed.

## Safety And Data Notes

- Do not commit `.env`; it may contain database passwords, JWT secrets, SMTP credentials, or LLM provider keys.
- Do not run `docker compose down -v` unless you intentionally want to delete the PostgreSQL volume.
- MoonCARE health and emotion features must remain non-diagnostic and for reference only.
- Keep logs free of full chat text, health privacy data, tokens, verification codes, and API keys.
