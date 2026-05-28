# Chat Agent Full Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the MoonCARE chat Agent optimization usable through the existing REST/SSE chat interfaces with safe caching, unified metadata, bounded context, and verifiable provider configuration.

**Architecture:** Keep the existing `PerceptionAgent -> Router -> Agent` safety route. Add a local bounded semantic cache behind the existing `get_semantic_cache()` contract, reuse it in REST and SSE only after perception confirms the turn is low risk, and keep ProductMemoryService plus conversation compaction as the context boundary.

**Tech Stack:** FastAPI, SQLAlchemy, unittest, Vue 3, Pinia, Axios/fetch SSE, OpenAI-compatible LLM provider configuration.

---

## File Structure

- Modify: `backend/app/services/semantic_cache_service.py`
  - Owns local in-process LRU semantic cache, TTL, similarity, stats, and no-op fallback contract.
- Modify: `backend/app/services/agent_service.py`
  - Owns Agent orchestration, semantic cache use, streaming fast path, action suggestions, and context compaction handoff.
- Modify: `backend/app/api/v1/chat.py`
  - Owns REST/SSE response envelope consistency and persistence.
- Modify: `backend/app/services/conversation_compaction_service.py`
  - Owns bounded recent window plus older summary behavior.
- Modify: `backend/app/config.py`
  - Owns cache/window configuration defaults.
- Modify: `.env.example`
  - Documents production-safe chat Agent configuration.
- Test: `backend/tests/test_semantic_cache.py`
- Test: `backend/tests/test_chat_agent_quality.py`
- Test: `backend/tests/test_chat_context_mechanism.py`
- Test: `backend/tests/test_vllm_integration.py`

## Tasks

### Task 1: Local Semantic Cache Contract

- [ ] Write failing tests in `backend/tests/test_semantic_cache.py` for exact match, phrase similarity, TTL expiry, LRU eviction, disabled dummy contract, and crisis-safe caller behavior.
- [ ] Run `python -m unittest backend.tests.test_semantic_cache -v` and confirm the new tests fail because the real cache is missing.
- [ ] Implement a local `LocalSemanticCache` in `backend/app/services/semantic_cache_service.py` using `OrderedDict`, normalized keys, token Jaccard similarity, TTL checks, and `get_cache_stats()`.
- [ ] Run `python -m unittest backend.tests.test_semantic_cache -v` and confirm pass.

### Task 2: REST And SSE Cache Fast Path

- [ ] Add failing tests in `backend/tests/test_chat_agent_quality.py` showing REST cache hits skip Router after low-risk perception, crisis text ignores cache, and streaming support can emit cached tokens plus an `end` chunk with `reply_status=cache_hit`.
- [ ] Run the targeted tests and confirm RED.
- [ ] Update `backend/app/services/agent_service.py` so `get_response()` and `get_streaming_response()` use semantic cache after perception and before Router/LLM, never before safety checks.
- [ ] Include `cache_hit` and `cache_similarity` in streaming `end` chunks.
- [ ] Run the targeted tests and confirm GREEN.

### Task 3: Unified Chat Interface Metadata

- [ ] Add failing tests that REST and SSE end payloads both expose `reply_status`, `elapsed_ms`, `cache_hit`, `cache_similarity`, `assessment_state`, and `memory_state`.
- [ ] Update `backend/app/api/v1/chat.py` to return those fields consistently while preserving existing `reply`, `actions`, and `suggestions`.
- [ ] Run the targeted chat API tests and confirm GREEN.

### Task 4: Bounded Context Window

- [ ] Add failing tests in `backend/tests/test_chat_context_mechanism.py` for recent 20-turn preservation, older summary insertion, and total context message count not exceeding 30.
- [ ] Update `ConversationCompactionService` and related config defaults to use a 20-turn recent layer and 30-turn total cap.
- [ ] Run `python -m unittest backend.tests.test_chat_context_mechanism -v` and confirm GREEN.

### Task 5: Configuration Documentation And Provider Contract

- [ ] Add failing tests in `backend/tests/test_vllm_integration.py` for cache/window config presence and provider list including `nvidia`, `openai`, `vllm`, `accelerated`, and `zai`.
- [ ] Update `backend/app/config.py` and `.env.example` with `SEMANTIC_CACHE_MAX_SIZE`, `CHAT_CONTEXT_RECENT_TURNS`, and `CHAT_CONTEXT_MAX_TURNS`.
- [ ] Run `python -m unittest backend.tests.test_vllm_integration -v` and confirm GREEN.

### Task 6: Final Verification

- [ ] Run `python -m compileall backend`.
- [ ] Run `python -m unittest backend.tests.test_p0_safety_and_prompts backend.tests.test_chat_agent_quality backend.tests.test_chat_context_mechanism backend.tests.test_chat_memory_service backend.tests.test_vllm_integration backend.tests.test_semantic_cache -v`.
- [ ] Run `cd frontend; npm run build`.
- [ ] Report any failures with exact command and reason.
