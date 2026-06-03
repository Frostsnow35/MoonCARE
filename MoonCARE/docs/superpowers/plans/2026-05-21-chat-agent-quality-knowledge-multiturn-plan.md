# Chat Agent Quality, Knowledge, and Multi-Turn Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 MoonCARE 聊天 Agent 的陪伴话术、知识问答接入可信度和同会话多轮发送失败问题。

**Architecture:** 先在后端 `ResponseQualityGuard` 做确定性质量兜底，再同步 `support_prompt.txt` 约束云端模型生成；知识问答保持现有 `KnowledgeAgent` 本地 RAG 文件加载链路并补回归测试；多轮失败通过 REST/SSE/WS 测试定位和修复。安全链路继续走 `PerceptionAgent -> Router -> Intervention/Knowledge/Support`。

**Tech Stack:** FastAPI, SQLAlchemy, unittest, Vue 3, Pinia, Vite, OpenAI-compatible LLM provider.

---

### Task 1: Support Reply Quality Guard

**Files:**
- Modify: `backend/app/services/response_quality_service.py`
- Modify: `backend/app/prompts/support_prompt.txt`
- Test: `backend/tests/test_chat_agent_quality.py`

- [ ] Add tests for short emotional disclosures:
  - `我有点难受` must not produce `低落`, `压下去`, `解释清楚`, `经前`, `经期`, `诊断`, or duplicate sentences.
  - The reply should contain soft oral phrasing such as `啦`, `呀`, `呢`, or a gentle emoji.
  - The reply should end with an open invitation, not a three-option classification question.
- [ ] Add a test for duplicate sentence repair where the same sentence appears twice.
- [ ] Implement sentence-level de-duplication in `ResponseQualityGuard.repair_reply()`.
- [ ] Replace short emotional-distress deterministic copy with “一次接纳 + 一次轻推”:
  - Reflect ambiguity: “心里/身体不太舒服”.
  - Use “可以” phrasing instead of “不要/不用急着”.
  - Defer menstrual context unless the user text itself mentions menstrual/cycle words.
  - Use one open invitation.
- [ ] Update `support_prompt.txt` with the same rules for generated responses.

### Task 2: Knowledge Agent Local RAG Verification

**Files:**
- Modify: `backend/tests/test_chat_agent_quality.py`
- Modify if needed: `backend/app/agents/knowledge_agent.py`

- [ ] Add tests that `KnowledgeAgent` loads `knowledge_base.json`.
- [ ] Add tests that a menstrual-health question retrieves a local card without requiring cloud LLM availability.
- [ ] If retrieval fallback is too brittle, tighten keyword matching without adding unsupported medical facts.

### Task 3: Same-Session Multi-Turn Regression

**Files:**
- Modify: `backend/tests/test_p0_chat_ws_auth.py`
- Modify if needed: `backend/app/api/v1/chat.py`
- Modify if needed: `frontend/src/stores/chat.js` or `frontend/src/views/Chat.vue`

- [ ] Add tests for two messages in the same WebSocket session.
- [ ] Add tests for two REST messages with the same `session_id`.
- [ ] Add tests for two SSE messages with the same `session_id`.
- [ ] Fix the failing layer only after the failing test identifies it.

### Task 4: Verification, Packaging, and Manual Run

**Files:**
- Update generated build output in `frontend/dist`
- Sync package output in `MoonCAREpack/frontend/dist`

- [ ] Run focused backend tests.
- [ ] Run full backend unittest discovery.
- [ ] Run `python -m compileall backend`.
- [ ] Run `npm run build`.
- [ ] Sync latest frontend build into `MoonCAREpack/frontend/dist`.
- [ ] Run `docker compose -f MoonCAREpack/docker-compose.yml config` with dummy required secrets.
- [ ] Start backend and frontend locally.
- [ ] Give the user manual test steps for `/chat`.
