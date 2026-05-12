# Chat Agent Menstrual Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix MoonCARE chat responses so ordinary sadness and discomfort are first understood in menstrual/body-emotion context, while crisis routing remains immediate.

**Architecture:** Keep the existing `PerceptionAgent -> Router -> SupportAgent` path. Add lightweight local semantic signals in `PerceptionAgent`, improve `SupportAgent` prompt rules, adjust `AgentService` action suggestions, and expand `LLMService` output cleanup.

**Tech Stack:** FastAPI backend, Python 3.10+, synchronous SQLAlchemy currently, unittest test suite, prompt templates under `backend/app/prompts/`.

---

## File Structure

- Modify: `backend/tests/test_p0_safety_and_prompts.py` for P0 regression tests.
- Modify: `backend/app/agents/perception_agent.py` to add menstrual/body-emotion semantic signals to state.
- Modify: `backend/app/prompts/support_prompt.txt` to enforce the response sequence:承接 -> 身体确认 -> 具象支持 -> 必要时安全提示.
- Modify: `backend/app/services/agent_service.py` to generate lower-pressure contextual action suggestions.
- Modify: `backend/app/agents/llm_service.py` to strip generated tags and role prefixes.
- Modify: `docs/技术文档-MoonCARE女性PMS情绪陪伴.md` to record the completed chat behavior change.

### Task 1: Regression Tests

**Files:**
- Modify: `backend/tests/test_p0_safety_and_prompts.py`

- [ ] **Step 1: Add failing tests**

Add tests that assert:

```python
def test_perception_extracts_menstrual_body_emotion_context(self):
    from app.agents.perception_agent import PerceptionAgent

    state = PerceptionAgent().analyze("例假来了，肚子绞痛，莫名其妙想哭")

    self.assertEqual(state["risk_level"], "medium")
    self.assertIn("pain", state["support_context"]["body_signals"])
    self.assertIn("tearful", state["support_context"]["emotion_signals"])
    self.assertTrue(state["support_context"]["menstrual_related"])


def test_low_sadness_actions_do_not_default_to_breathing(self):
    from app.services.agent_service import AgentService

    service = AgentService()
    actions = service._generate_action_suggestions({
        "risk_level": "medium",
        "message": "我今天很难过，莫名其妙想哭",
        "support_context": {
            "menstrual_related": True,
            "body_signals": [],
            "emotion_signals": ["sad", "tearful"],
        },
    })

    self.assertNotEqual(actions[0]["action"], "breathing")
    self.assertTrue(any(action["action"] == "diary" for action in actions))


def test_period_pain_actions_prioritize_warmth_and_rest(self):
    from app.services.agent_service import AgentService

    service = AgentService()
    actions = service._generate_action_suggestions({
        "risk_level": "medium",
        "message": "例假来了，肚子绞痛，特别无助",
        "support_context": {
            "menstrual_related": True,
            "body_signals": ["pain"],
            "emotion_signals": ["helpless", "tearful"],
        },
    })

    self.assertEqual(actions[0]["action"], "warmth")
    self.assertIn("热", actions[0]["description"])


def test_llm_cleanup_removes_chatting_and_role_labels(self):
    from app.agents.llm_service import LLMService

    service = LLMService.__new__(LLMService)
    cleaned = service._clean_response("_chatting_ 情绪宝宝：<think>hidden</think>我在这里陪你。")

    self.assertEqual(cleaned, "我在这里陪你。")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts -v`

Expected: the new tests fail because `support_context` does not exist, sadness actions still prioritize current defaults in some paths, and `_chatting_` is not cleaned.

### Task 2: Semantic State and Action Suggestions

**Files:**
- Modify: `backend/app/agents/perception_agent.py`
- Modify: `backend/app/services/agent_service.py`
- Test: `backend/tests/test_p0_safety_and_prompts.py`

- [ ] **Step 1: Implement support_context in PerceptionAgent**

Add local keyword extraction for body signals (`pain`, `bloating`, `fatigue`, `sleep_change`, `appetite`) and emotion signals (`sad`, `tearful`, `irritable`, `anxious`, `helpless`). Set `menstrual_related` when the message mentions menstrual terms, body signals, or the cycle phase is `经前期`, `黄体期`, `luteal`, `menstrual`, `经期`.

- [ ] **Step 2: Adjust action suggestion ordering**

In `_generate_action_suggestions`, use `support_context` first. For body pain, add:

```python
{
    "action": "warmth",
    "label": "暖一暖小腹",
    "description": "用热水袋或温热毛巾暖一下小腹，先让身体松一点",
    "route": None,
}
```

For ordinary sadness/tearfulness, prefer diary or rest before breathing. Keep breathing first only for anxiety/panic keywords or `risk_level in ["high", "crisis"]`.

- [ ] **Step 3: Run tests and verify GREEN for Task 2**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts -v`

Expected: semantic/action tests pass; cleanup test may still fail until Task 3.

### Task 3: Prompt and Output Cleanup

**Files:**
- Modify: `backend/app/prompts/support_prompt.txt`
- Modify: `backend/app/agents/llm_service.py`
- Test: `backend/tests/test_p0_safety_and_prompts.py`

- [ ] **Step 1: Update Support prompt**

Add rules that require:

- first sentence names the feeling and possible body burden;
- second sentence asks one gentle body-state question when relevant;
- third sentence gives one concrete support action;
- professional help appears only for severe, persistent, or crisis-like content;
- every health/PMS statement remains “仅供参考，不替代诊断”.

- [ ] **Step 2: Expand `_clean_response`**

Strip common generated artifacts: `_chatting_`, `<think>...</think>`, `assistant:`, `情绪宝宝：`, `守护宝宝：`, `回复：`, leading bullets, and repeated blank lines.

- [ ] **Step 3: Run tests and verify GREEN**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts -v`

Expected: all P0 tests pass.

### Task 4: Documentation and Full Verification

**Files:**
- Modify: `docs/技术文档-MoonCARE女性PMS情绪陪伴.md`

- [ ] **Step 1: Update technical documentation**

Add a dated section describing the completed chat-agent behavior change, affected files, and safety boundary.

- [ ] **Step 2: Run related backend tests**

Run: `python -m unittest backend.tests.test_p0_safety_and_prompts backend.tests.test_p1_assessment_loop -v`

Expected: all selected tests pass.

- [ ] **Step 3: Run compile check**

Run: `python -m compileall backend`

Expected: compile completes without syntax errors.

- [ ] **Step 4: Review diff before commit**

Run: `git diff -- backend/app/agents/perception_agent.py backend/app/services/agent_service.py backend/app/agents/llm_service.py backend/app/prompts/support_prompt.txt backend/tests/test_p0_safety_and_prompts.py docs/技术文档-MoonCARE女性PMS情绪陪伴.md docs/superpowers/specs/2026-05-13-chat-agent-menstrual-support-spec.md docs/superpowers/plans/2026-05-13-chat-agent-menstrual-support-plan.md`

Expected: diff only contains the scoped behavior, tests, and docs.

