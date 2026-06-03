# Chat WebSocket Auth Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make MoonCARE chat WebSocket authentication and chat session writes trust JWT identity only, not client-supplied `user_id` or another user's `session_id`.

**Architecture:** Keep the existing `/api/v1/chat/ws/{user_id}` route for compatibility, add a token-authenticated `/api/v1/chat/ws` route for the frontend, and route both through one authenticated WebSocket handler. REST and SSE chat writes will reject a `session_id` that already belongs to another user.

**Tech Stack:** FastAPI WebSocket, PyJWT, SQLAlchemy Session, Vue 3 Pinia chat store, unittest/TestClient.

---

## File Map

| File | Responsibility |
| --- | --- |
| `backend/tests/test_p0_chat_ws_auth.py` | Regression tests for WebSocket token enforcement, path `user_id` spoofing, and cross-user session write rejection. |
| `backend/app/api/v1/chat.py` | Decode WebSocket token, ignore legacy path `user_id`, centralize session ownership checks, and apply them to REST/SSE writes. |
| `frontend/src/stores/chat.js` | Build WebSocket URLs with the current access token and no hardcoded `user_id`. |
| `MoonCAREpack/backend/app/api/v1/chat.py` | Deployment package copy of the backend chat route after verification. |
| `MoonCAREpack/frontend/dist` | Rebuilt frontend deployment assets after the store change. |

## Tasks

### Task 1: Red Tests For WebSocket Auth And Session Isolation

- [ ] Add `backend/tests/test_p0_chat_ws_auth.py` with tests that:
  - connect to `/api/v1/chat/ws/1` without `token` and expect WebSocket close code `1008`;
  - connect to `/api/v1/chat/ws/{other_user_id}?token=<current_user_token>` and verify saved conversations use the token user, not the path user;
  - call `/api/v1/chat/message` and `/api/v1/chat/stream` with a `session_id` owned by another user and expect `404`.

- [ ] Run `python -m unittest backend.tests.test_p0_chat_ws_auth -v`.

Expected red state: no-token WebSocket is accepted, path `user_id` controls writes, and cross-user `session_id` writes are not rejected.

### Task 2: Backend Auth And Session Ownership

- [ ] In `backend/app/api/v1/chat.py`, add a helper that extracts `token` from `websocket.query_params`, decodes it with `settings.SECRET_KEY` and `settings.ALGORITHM`, verifies the user exists, and closes the socket with policy violation code `1008` when invalid.

- [ ] Add `_ensure_chat_session_access(db, user_id, session_id)`:
  - if `session_id` is empty, do nothing;
  - if no conversation exists for that session, allow creation;
  - if the first existing conversation belongs to the current user, allow;
  - otherwise raise `HTTPException(status_code=404, detail="会话不存在")`.

- [ ] Route both `/ws` and `/ws/{path_user_id}` into one authenticated WebSocket flow and use the token-derived user id. The legacy path id must not influence database writes.

- [ ] Call `_ensure_chat_session_access` in REST `/message` and SSE `/stream` before writing or streaming a response.

### Task 3: Frontend WebSocket Token URL

- [ ] In `frontend/src/stores/chat.js`, make `getWebSocketUrl()` read `access_token` from `localStorage` and return `/api/v1/chat/ws?token=<encoded token>`.

- [ ] Make `connectWebSocket()` refuse to connect when there is no token, set `lastError`, and stop reconnect scheduling until login state is restored.

### Task 4: Green Tests And Package Sync

- [ ] Run `python -m unittest backend.tests.test_p0_chat_ws_auth -v`.
- [ ] Run `python -m unittest discover backend/tests -v`.
- [ ] Run `python -m compileall backend`.
- [ ] Run `npm run build` in `frontend`.
- [ ] Copy changed backend app files and rebuilt `frontend/dist` into `MoonCAREpack`.
- [ ] Run `python -m compileall MoonCAREpack\backend\app`.
- [ ] Run `docker compose -f MoonCAREpack\docker-compose.yml config` with dummy required env vars.
- [ ] Run `git diff --check`.

## Risk Notes

| Risk | Handling |
| --- | --- |
| WebSocket browser clients cannot set `Authorization` headers | Use a `token` query parameter for now; require HTTPS/WSS in deployment and avoid logging full query strings at the reverse proxy. |
| Existing clients still call `/ws/{user_id}` | Keep the legacy route but ignore the path `user_id`; token identity wins. |
| Cross-user `session_id` reuse | Reject writes to sessions already owned by another user. |
| Crisis safety regression | Do not touch agent routing, prompt loading, or safety fallback behavior; run existing P0 safety tests. |
