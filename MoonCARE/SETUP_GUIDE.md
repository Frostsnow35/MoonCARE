# MoonCARE Setup Guide

> Change date: 2026-05-26  
> Impact scope: local collaborator setup, dependency installation, and development startup  
> Status: completed for local setup; production deployment still needs server-specific verification

## 1. Goal

Make a fresh checkout start with one setup command and one dev command:

```bash
npm run setup
npm run dev
```

This keeps MoonCARE on the current backend `FastAPI + SQLAlchemy` and frontend `Vue 3 + Pinia + Vite` architecture. It does not change the AI safety routing layer.

## 2. Prerequisites

| Dependency | Version | Notes |
| --- | --- | --- |
| Python | 3.10+ | Used for FastAPI and the setup launcher |
| Node.js | 20+ | Used for root scripts and Vite |
| npm | 10+ | Installed with Node.js |

## 3. First-Time Setup

Run from the repository root:

```bash
npm run setup
```

The setup script performs:

| Step | Status | Output |
| --- | --- | --- |
| Copy env examples | Completed | Creates `.env`, `backend/.env`, `frontend/.env` only when missing |
| Install backend dependencies | Completed | Uses `backend/requirements.txt` |
| Install root npm dependencies | Completed | Uses root `package.json` |
| Install frontend dependencies | Completed | Uses `frontend/package.json` |

## 4. Start Development Servers

Run from the repository root:

```bash
npm run dev
```

The launcher starts:

| Service | URL | Log |
| --- | --- | --- |
| Backend | `http://localhost:8000` | `logs/backend-dev.log` |
| Frontend | `http://localhost:3000` | `logs/frontend-dev.log` |

Stop both services with `Ctrl+C`.

## 5. Optional AI Runtime Dependencies

Default setup intentionally excludes heavyweight local inference packages. They are not required for a collaborator to start the app and verify the core UI/API.

Install only when needed:

```bash
python -m pip install -r backend/requirements-optional-ai.txt
```

| Package | Status | Reason |
| --- | --- | --- |
| `sentence-transformers` | Optional | Local embedding model support |
| `vllm` | Optional, skipped on Windows | Local GPU inference server; OS/GPU-specific |

Remote OpenAI-compatible providers remain configured through environment variables.

## 6. Common Checks

```bash
python -m compileall backend
npm run build
```

If `python` is not available on Windows, use the repository wrapper:

```bash
node scripts/run_python.js -m compileall backend
```

## 7. Safety and Configuration Notes

| Topic | Requirement |
| --- | --- |
| Crisis handling | Do not bypass `PerceptionAgent`, `Router`, or intervention fallback |
| Medical wording | AI output must stay reference-only and must not diagnose |
| Secrets | Never commit `.env`, API keys, JWT secrets, or database passwords |
| Logs | Do not log full sensitive chat, token, LLM key, or health privacy data |
| Production | Recheck CORS, `SECRET_KEY`, database URL, reverse proxy, WebSocket upgrade, and HTTPS |

## 8. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Missing command: npm` | Install Node.js 20+ and reopen the terminal |
| `Python 3.10+ is required` | Install Python 3.10+ and ensure it is on `PATH` |
| `Root dependencies are missing` | Run `npm run setup` |
| `Frontend dependencies are missing` | Run `npm run setup` |
| Backend exits immediately | Check `logs/backend-dev.log` |
| Frontend exits immediately | Check `logs/frontend-dev.log` |
