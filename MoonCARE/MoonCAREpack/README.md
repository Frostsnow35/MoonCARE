# MoonCAREpack

MoonCAREpack is the Docker-first, GitHub-ready package for MoonCARE（她语）. It contains backend source, frontend source, database schema/migrations, knowledge-base files, and local music assets. It must not contain real `.env` files, runtime databases, logs, cache files, or user privacy data.

> Change date: 2026-05-26  
> Scope: package structure, GitHub handoff, Docker/server deployment, local development startup  
> Status: ready for verification

## Included

| Area | Status | Notes |
| --- | --- | --- |
| Backend | Done | FastAPI source in `backend/app`, tests in `backend/tests` |
| Frontend | Done | Vue 3 source in `frontend/src`; `frontend/dist` is generated during build and ignored |
| Database | Done | PostgreSQL is provided by Docker Compose volume; SQLAlchemy creates tables on startup; Alembic migrations are included in `backend/migrations` |
| Knowledge base | Done | `backend/app/data/knowledge_base.json`, embeddings, and PSST flow data are included |
| Music | Done | Local test music files are in `backend/music`; Docker persists this directory in `music_data`; runtime uploads matching `backend/music/upload-*` are ignored by Git |
| Secrets | Done | `.env.example` is included; `.env` is ignored and must be created locally or on server |

## Local Development

Prerequisites:

- Python 3.10+
- Node.js 20+
- npm 10+

Setup:

```bash
cd MoonCAREpack
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
npm install
cd frontend
npm install
cd ..
cp .env.example .env
```

For quick local development, edit `.env`:

```env
DEBUG=true
AUTH_EMAIL_DELIVERY_MODE=log
DATABASE_URL=sqlite:///./healthai.db
LLM_PROVIDER=nvidia
NVIDIA_API_KEY=
```

Run both backend and frontend:

```bash
npm run dev
```

Open:

```text
Frontend: http://127.0.0.1:3000
Backend:  http://127.0.0.1:8000
Health:   http://127.0.0.1:8000/healthz
```

The local SQLite file `healthai.db` is runtime data and is ignored by Git. Docker deployments use PostgreSQL instead.

## Docker / Server Deployment

Prerequisites:

- Docker Engine
- Docker Compose v2 (`docker compose version`)
- Network access for pulling `node:20-alpine`, `python:3.11-slim`, and `postgres:15-alpine`

Run:

```bash
cd MoonCAREpack
bash deploy.sh
```

The script will:

- create `.env` from `.env.example` if missing
- generate `DB_PASSWORD` and `SECRET_KEY` when placeholders are still present
- validate Docker Compose config
- build frontend source inside the Docker image
- build and start FastAPI + PostgreSQL
- keep PostgreSQL data in the `postgres_data` Docker volume
- keep bundled and uploaded music files in the `music_data` Docker volume
- wait for `http://127.0.0.1:18000/health`

Open after deployment:

```text
http://127.0.0.1:18000
```

Useful commands:

```bash
docker compose ps
curl -fsS http://127.0.0.1:18000/health
curl -fsS http://127.0.0.1:18000/healthz
bash diagnose.sh
```

Force a clean rebuild after code changes:

```bash
FORCE_REBUILD=1 bash deploy.sh
```

Do not run `docker compose down -v` unless you intentionally want to delete the PostgreSQL volume, the music volume, and all stored user data.

## GitHub Handoff Rules

Commit these:

- source code under `backend/` and `frontend/`
- `backend/app/data/*` knowledge files
- `backend/migrations/*`
- approved local music assets in `backend/music`
- `.env.example`, Docker files, scripts, and docs

Do not commit these:

- `.env`, `.env.local`, `.env.production`
- `healthai.db`, `*.sqlite`, database journals/WAL files
- `frontend/dist`, `backend/dist`
- `node_modules`, `.venv`, `__pycache__`
- logs, screenshots, temporary verification artifacts
- uploaded user music files named `backend/music/upload-*`

## Safety Notes

MoonCARE serves menstrual-cycle emotion support and health companionship. AI responses must remain non-diagnostic and for reference only. Crisis signals must continue through the safety/intervention path before any business goal. Logs must not contain full chat text, health privacy data, tokens, verification codes, API keys, or database passwords.
