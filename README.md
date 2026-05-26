# MoonCARE Local Startup

MoonCARE is an existing women-focused menstrual emotion companionship and health support project. This repository is not a blank starter; local startup should preserve the current FastAPI + Vue architecture.

## Quick Start

Prerequisites:

| Tool | Required |
| --- | --- |
| Python | 3.10 or later |
| Node.js | 20 or later |
| npm | 10 or later |

From the repository root:

```bash
npm run setup
npm run dev
```

Then open:

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

Logs are written to `logs/backend-dev.log` and `logs/frontend-dev.log`.

## What `npm run setup` Does

Status: completed.

| Step | Description |
| --- | --- |
| Environment files | Copies `.env.example`, `backend/.env.example`, and `frontend/.env.example` when local `.env` files are missing |
| Backend dependencies | Installs `backend/requirements.txt` with the current Python interpreter |
| Root dependencies | Installs root npm scripts and `concurrently` |
| Frontend dependencies | Installs `frontend/package.json` dependencies |

Optional local inference packages are not installed by default. If you need local embeddings or vLLM, run:

```bash
python -m pip install -r backend/requirements-optional-ai.txt
```

`vllm` is skipped on Windows by that optional requirements file because it is OS/GPU-specific. Use the OpenAI-compatible remote provider configuration for normal collaboration startup.

## Manual Startup

If you need separate terminals:

```bash
node scripts/run_python.js -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
cd backend; 
pip install -r requirements.txt; 
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Local Test Account

According to the current code, local `DEBUG=true` supports this reproducible development account:

| Email | Password |
| --- | --- |
| `test@mooncare.local` | `test123456` |

Keep `DEBUG=false` for production and public deployments.

## Safety Notes

Status: needs verification before production.

| Risk | Mitigation |
| --- | --- |
| Secrets leakage | Do not commit `.env`, API keys, JWT secrets, or database passwords |
| LLM timeout | Keep configured timeout/fallback behavior enabled |
| Health or emotion safety | Do not bypass the existing PerceptionAgent, Router, or crisis intervention path |
| Local SQLite limits | Use PostgreSQL for multi-user or server deployments |
| Optional AI dependencies | Keep heavy local inference packages out of the default setup path |
