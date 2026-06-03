# Chat Memory Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add safe persistent chat memory and mode-specific Agent guidance to MoonCARE chat.

**Architecture:** Persist user-level memory summaries in `chat_memories`; build a bounded prompt context from recent `Conversation` turns plus long-term memories before routing; keep PerceptionAgent and Router as the safety gate for all modes.

**Tech Stack:** FastAPI, SQLAlchemy, SQLite, Python unittest, Vue 3 Composition API, Pinia, Axios.

---

### Task 1: Backend Memory Model and Service

**Files:**
- Create: `backend/app/models/chat_memory.py`
- Create: `backend/app/services/chat_memory_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/user.py`
- Test: `backend/tests/test_chat_memory_service.py`

- [ ] Write tests for capturing user preferences, PMS/emotion traits, recent context building, and crisis-skip behavior.
- [ ] Run `python -m unittest backend.tests.test_chat_memory_service -v` and confirm the tests fail before implementation.
- [ ] Implement `ChatMemory` and `ChatMemoryService` with bounded summaries and no full-message logging.
- [ ] Run the same tests and confirm they pass.

### Task 2: Agent Context Injection and Mode Guidance

**Files:**
- Modify: `backend/app/services/agent_service.py`
- Modify: `backend/app/agents/support_agent.py`
- Modify: `backend/app/agents/knowledge_agent.py`
- Modify: `backend/app/agents/llm_service.py`
- Modify: `backend/app/prompts/support_prompt.txt`
- Modify: `backend/app/prompts/knowledge_prompt.txt`
- Modify: `backend/app/prompts/knowledge_fallback_prompt.txt`
- Modify: `backend/app/prompts/default_chat_prompt.txt`
- Test: `backend/tests/test_p0_safety_and_prompts.py`

- [ ] Add tests proving memory context reaches the selected Agent and crisis routing still ignores `agent_mode`.
- [ ] Run the P0 tests and confirm the new memory-context test fails.
- [ ] Add mode guidance and memory/recent context placeholders to prompt rendering.
- [ ] Run P0 tests and confirm they pass.

### Task 3: Chat API/WebSocket Integration

**Files:**
- Modify: `backend/app/api/v1/chat.py`
- Test: `backend/tests/test_p1_assessment_loop.py`

- [ ] Add tests proving REST chat returns `memory_state` and writes memory after a safe user turn.
- [ ] Run P1 tests and confirm the new test fails.
- [ ] Integrate `ChatMemoryService` into REST and WebSocket paths using the same flow.
- [ ] Run P1 tests and confirm they pass.

### Task 4: Frontend Store and Chat Surface

**Files:**
- Modify: `frontend/src/stores/chat.js`
- Modify: `frontend/src/views/Chat.vue`

- [ ] Add `memoryState` to `chatStore`, reset it with chat clear, and update it from REST/WebSocket responses.
- [ ] Add a subtle memory-aware status line that does not expose sensitive details.
- [ ] Keep all message rendering as text interpolation and avoid `v-html`.

### Task 5: Verification and Documentation

**Files:**
- Modify: `docs/技术文档-MoonCARE女性PMS情绪陪伴.md`

- [ ] Update the technical document with the chat memory architecture, API field, and risk controls.
- [ ] Run `python -m unittest backend.tests.test_chat_memory_service backend.tests.test_p0_safety_and_prompts backend.tests.test_p1_assessment_loop -v`.
- [ ] Run `python -m compileall backend/app backend/tests`.
- [ ] Run `npm run build` in `frontend`; if Vite/esbuild fails because of environment permissions, report exact output.
