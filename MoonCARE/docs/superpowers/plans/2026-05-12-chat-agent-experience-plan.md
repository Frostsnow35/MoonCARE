# Chat Agent Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a safer, warmer, role-aware MoonCARE chat experience without bypassing the existing Agent risk router.

**Architecture:** The frontend stores only a user role preference and sends it to `/api/v1/chat`; the backend treats it as a routing hint after PerceptionAgent risk analysis. Crisis/high risk always overrides the preference and routes to InterventionAgent or the safe fallback.

**Tech Stack:** Vue 3 Composition API, Pinia, Axios, FastAPI, SQLAlchemy, Python unittest.

---

### Task 1: Backend Safe Role Preference

**Files:**
- Modify: `backend/tests/test_p0_safety_and_prompts.py`
- Modify: `backend/app/agents/router.py`
- Modify: `backend/app/services/agent_service.py`
- Modify: `backend/app/api/v1/chat.py`

- [x] Add failing tests that `agent_mode="knowledge"` routes low-risk messages to KnowledgeAgent and crisis messages still route to InterventionAgent.
- [x] Run `python -m unittest backend.tests.test_p0_safety_and_prompts -v` and confirm the new tests fail because `Router.route()` does not accept `agent_mode`.
- [x] Add optional `agent_mode` to `Router.route()` and only apply it after crisis/high checks.
- [x] Thread `agent_mode` through `AgentService.get_response()`, REST `/chat/message`, and WebSocket payload handling.
- [x] Run `python -m unittest backend.tests.test_p0_safety_and_prompts -v` and confirm it passes.

### Task 2: Frontend Chat State

**Files:**
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/stores/chat.js`

- [x] Add `agentMode`, `isAwaitingReply`, `lastError`, and bootstrapped welcome-message helpers to `chatStore`.
- [x] Ensure `sendMessage()` sends `{ message, agent_mode }` over WebSocket.
- [x] Ensure `chatAPI.sendMessage()` includes optional `agent_mode` in REST params.
- [x] Keep `assessmentState` hidden and clear it with chat clear.

### Task 3: Chat Page Interaction UI

**Files:**
- Replace focused sections in `frontend/src/views/Chat.vue`

- [x] Render a polished mobile chat surface with header, role segmented control, status chip, assistant welcome, messages, suggestions, typing state, error state, and fixed input composer.
- [x] Keep all user/assistant content as text interpolation, never `v-html`.
- [x] Use existing Tailwind utility style and simple semantic CSS scoped to the page.
- [x] Preserve interview compatibility enough to avoid breaking the existing home entry, but do not make it the primary chat flow.

### Task 4: Verification

**Files:**
- No source changes unless verification finds a defect.

- [x] Run `python -m unittest backend.tests.test_p0_safety_and_prompts backend.tests.test_p1_assessment_loop -v`.
- [x] Run `npm run build` in `frontend`.
- [x] If Vite/esbuild still fails with `spawn EPERM`, report the exact failure instead of claiming frontend build success.
