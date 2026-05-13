# GLM Chat Latency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure MoonCARE chat returns a model reply or safe timeout fallback within 15-20 seconds when GLM-5.1 is slow.

**Architecture:** Keep the existing safety route and GLM-5.1 quality path. Add a generic OpenAI-compatible acceleration provider for vLLM/SGLang/LMDeploy-style endpoints, configurable LLM/client deadlines, worker-thread execution for blocking Router/LLM work, structured `reply_status` and `elapsed_ms`, and frontend timeout alignment.

**Tech Stack:** FastAPI, Python 3.10+, OpenAI-compatible client, Vue 3, Axios, unittest.

---

## File Structure

- Modify: `backend/app/config.py` for timeout settings.
- Modify: `backend/app/agents/llm_service.py` to use configurable client timeout.
- Modify: `backend/app/services/agent_service.py` to enforce chat reply deadline and timeout fallback.
- Modify: `backend/app/api/v1/chat.py` to return `reply_status` and `elapsed_ms`.
- Modify: `frontend/src/api/index.js` to align Axios timeout.
- Modify: `frontend/src/views/Chat.vue` to align local wait timeout and timeout fallback copy.
- Modify: `backend/tests/test_p0_safety_and_prompts.py` for timeout behavior tests.
- Modify: `backend/tests/test_vllm_integration.py` for accelerated provider configuration tests.
- Modify: `docs/技术文档-MoonCARE女性PMS情绪陪伴.md` for completed behavior notes.

### Task 1: Tests for Deadline Behavior

**Files:**
- Modify: `backend/tests/test_p0_safety_and_prompts.py`

- [ ] **Step 1: Add failing tests**

Add tests:

```python
def test_agent_service_timeout_returns_fallback_quickly(self):
    from app.services.agent_service import AgentService
    import asyncio
    import time

    class PassivePerception:
        def analyze(self, message: str, cycle_phase=None, sensor_data=None):
            return {"risk_level": "low", "cycle_phase": cycle_phase or "经前期"}

    class SlowRouter:
        def route(self, message: str, state: dict, agent_mode: str = "auto"):
            time.sleep(0.2)
            return "late model reply", "support"

    service = AgentService()
    service.perception = PassivePerception()
    service.router = SlowRouter()
    service.reply_timeout_seconds = 0.01

    start = time.perf_counter()
    result = asyncio.run(service.get_response(1, "timeout-test", "我有点难过", {}, "support"))
    elapsed = time.perf_counter() - start

    self.assertLess(elapsed, 0.15)
    self.assertEqual(result["intent"], "timeout_fallback")
    self.assertEqual(result["reply_status"], "timeout_fallback")
    self.assertIn("先", result["message"])
    self.assertGreaterEqual(result["elapsed_ms"], 0)


def test_agent_service_crisis_timeout_uses_safe_fallback(self):
    from app.services.agent_service import AgentService
    import asyncio
    import time

    class CrisisPerception:
        def analyze(self, message: str, cycle_phase=None, sensor_data=None):
            return {"risk_level": "crisis", "cycle_phase": "未知"}

    class SlowRouter:
        def route(self, message: str, state: dict, agent_mode: str = "auto"):
            time.sleep(0.2)
            return "late model reply", "intervention"

    service = AgentService()
    service.perception = CrisisPerception()
    service.router = SlowRouter()
    service.reply_timeout_seconds = 0.01

    result = asyncio.run(service.get_response(1, "crisis-timeout", "我想自残", {}, "auto"))

    self.assertEqual(result["intent"], "timeout_fallback")
    self.assertEqual(result["reply_status"], "timeout_fallback")
    self.assertIn("可信任的人", result["message"])
```

- [ ] **Step 2: Verify RED**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts -v`

Expected: the new tests fail because `reply_timeout_seconds`, `reply_status`, and `elapsed_ms` are not implemented.

### Task 2: Backend Deadline Implementation

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/agents/llm_service.py`
- Modify: `backend/app/services/agent_service.py`

- [ ] **Step 1: Add settings**

Add:

```python
LLM_REQUEST_TIMEOUT_SECONDS: float = 18.0
CHAT_AGENT_REPLY_TIMEOUT_SECONDS: float = 18.0
```

- [ ] **Step 2: Use configured LLM timeout**

In `LLMService.__init__`, replace fixed `timeout=60.0` with `timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS`.

- [ ] **Step 3: Enforce AgentService deadline**

Use `asyncio.wait_for(asyncio.to_thread(router.route, ...), timeout=self.reply_timeout_seconds)`. On timeout, return a fallback built from `risk_level` and crisis keywords.

- [ ] **Step 4: Verify GREEN**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts -v`

Expected: all P0 tests pass.

### Task 3: OpenAI-Compatible Acceleration Provider

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/agents/llm_service.py`
- Modify: `backend/tests/test_vllm_integration.py`

- [ ] **Step 1: Add failing provider test**

Add a test that sets:

```python
with patch.dict(os.environ, {
    "LLM_PROVIDER": "accelerated",
    "ACCELERATED_LLM_BASE_URL": "http://127.0.0.1:30000/v1",
    "ACCELERATED_LLM_API_KEY": "test-key",
    "ACCELERATED_LLM_MODEL_NAME": "glm-5.1",
}, clear=False):
    ...
```

Patch `app.agents.llm_service.OpenAI`, construct `LLMService()`, and assert `service.model == "glm-5.1"` and OpenAI received the normalized base URL.

- [ ] **Step 2: Implement provider config**

Add settings:

```python
ACCELERATED_LLM_BASE_URL: str = "http://localhost:30000/v1"
ACCELERATED_LLM_API_KEY: str = "accelerated-local"
ACCELERATED_LLM_MODEL_NAME: str = "glm-5.1"
ACCELERATED_LLM_ENGINE: str = "openai-compatible"
```

In `LLMService.__init__`, support `LLM_PROVIDER=accelerated`, using those settings. Keep existing `vllm`, `openai`, and `nvidia` providers.

- [ ] **Step 3: Verify provider test**

Run: `python -m unittest backend.tests.test_vllm_integration -v`

Expected: accelerated provider test passes without a real engine because the OpenAI client is mocked.

### Task 4: API and Frontend Alignment

**Files:**
- Modify: `backend/app/api/v1/chat.py`
- Modify: `frontend/src/api/index.js`
- Modify: `frontend/src/views/Chat.vue`

- [ ] **Step 1: Include backend status fields**

Add `reply_status` and `elapsed_ms` to REST and WebSocket assistant payloads from `AgentService.get_response()`.

- [ ] **Step 2: Align frontend timeout**

Set Axios timeout to `25000` and `CHAT_REPLY_TIMEOUT_MS` to `22000`. If `result.reply_status === 'timeout_fallback'`, show a non-error hint that GLM-5.1 was slow and retry is available.

- [ ] **Step 3: Run build**

Run: `npm run build` in `frontend`.

Expected: Vite build succeeds.

### Task 5: Documentation and Full Verification

**Files:**
- Modify: `docs/技术文档-MoonCARE女性PMS情绪陪伴.md`

- [ ] **Step 1: Update docs**

Add a 2026-05-13 section documenting GLM-5.1 latency controls, fields, defaults, and safety behavior.

- [ ] **Step 2: Run related backend tests**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts backend.tests.test_p1_assessment_loop -v`

Expected: all selected tests pass.

- [ ] **Step 3: Run compile check**

Run: `python -m compileall backend`

Expected: no syntax errors.
