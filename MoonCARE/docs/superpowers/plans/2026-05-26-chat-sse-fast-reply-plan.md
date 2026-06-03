# Chat SSE Fast Reply Implementation Plan

> Change date: 2026-05-26
> Impact scope: `backend/app/api/v1/chat.py`, `backend/app/services/agent_service.py`, `backend/app/services/response_quality_service.py`, `frontend/src/api/index.js`, `frontend/src/stores/chat.js`, `frontend/src/views/Chat.vue`, chat regression tests
> Status: in progress

## Goal

Unify the main chat experience on SSE and make emotional first turns receive a fast, gentle acknowledgement before slower Agent/LLM continuation finishes.

## Root Cause

The current chat page mixes direct `fetch()` SSE, REST fallback, and an unused WebSocket store path. The screenshot error is caused by the frontend `AbortController` cancelling `/chat/stream` when the first chunk is not received quickly enough. Because the page then falls back through another API path, UI state and persisted session state can diverge.

## Implementation Steps

1. Add regression coverage for streaming fast acknowledgement and frontend transport unification.
2. Make `ResponseQualityGuard.fast_ack_if_applicable()` return a short support acknowledgement for first emotional/body-discomfort turns.
3. Make `AgentService.get_streaming_response()` emit `start`, then fast `ack`/`token`, then continue LLM/Agent work when safe.
4. Make `/chat/stream` persist final response once and include assessment, memory, actions, suggestions, and status in the final event.
5. Move SSE parsing into `chatAPI.sendMessageStream()` and remove REST fallback/WebSocket sending from the chat page.
6. Simplify `chatStore` to session/message/persistence state for SSE.
7. Verify with backend unittest, frontend build, and a local `/healthz`/stream smoke check when possible.

## Safety Notes

The fast acknowledgement must not bypass crisis detection. Crisis/self-harm turns still return the safe intervention fallback and must not call ordinary support or knowledge routes first. Health-related advice remains reference-only and non-diagnostic.
