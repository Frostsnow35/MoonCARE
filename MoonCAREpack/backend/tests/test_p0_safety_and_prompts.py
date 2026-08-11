import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class _FakeAgent:
    def __init__(self, reply: str):
        self.reply = reply

    def respond(self, message: str, state: dict) -> str:
        return self.reply


class _FailingAgent:
    def respond(self, message: str, state: dict) -> str:
        raise RuntimeError("LLM unavailable")


class P0SafetyAndPromptTests(unittest.TestCase):
    def test_perception_marks_self_harm_language_as_crisis(self):
        from app.agents.perception_agent import PerceptionAgent

        agent = PerceptionAgent()

        for message in ["我有点想自残", "我想轻生", "I want to kill myself"]:
            with self.subTest(message=message):
                state = agent.analyze(message)
                self.assertEqual(state["risk_level"], "crisis")

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

    def test_crisis_route_takes_priority_over_knowledge_keywords(self):
        from app.agents.router import Router

        router = Router()
        router._support = _FakeAgent("support")
        router._knowledge = _FakeAgent("knowledge")
        router._intervention = _FakeAgent("intervention")

        reply, agent_name = router.route(
            "我想死，为什么经前会这么难受？",
            {"risk_level": "crisis", "cycle_phase": "经前期"},
        )

        self.assertEqual(reply, "intervention")
        self.assertEqual(agent_name, "intervention")

    def test_low_risk_knowledge_mode_prefers_knowledge_agent(self):
        from app.agents.router import Router

        router = Router()
        router._support = _FakeAgent("support")
        router._knowledge = _FakeAgent("knowledge")
        router._intervention = _FakeAgent("intervention")

        reply, agent_name = router.route(
            "我想了解经前为什么容易烦躁",
            {"risk_level": "low", "cycle_phase": "经前期"},
            agent_mode="knowledge",
        )

        self.assertEqual(reply, "knowledge")
        self.assertEqual(agent_name, "knowledge")

    def test_crisis_route_ignores_knowledge_mode_preference(self):
        from app.agents.router import Router

        router = Router()
        router._support = _FakeAgent("support")
        router._knowledge = _FakeAgent("knowledge")
        router._intervention = _FakeAgent("intervention")

        reply, agent_name = router.route(
            "我想自残，也想了解PMS",
            {"risk_level": "crisis", "cycle_phase": "经前期"},
            agent_mode="knowledge",
        )

        self.assertEqual(reply, "intervention")
        self.assertEqual(agent_name, "intervention")

    def test_crisis_route_uses_safe_fallback_when_intervention_fails(self):
        from app.agents.router import Router

        router = Router()
        router._support = _FakeAgent("support")
        router._knowledge = _FakeAgent("knowledge")
        router._intervention = _FailingAgent()

        reply, agent_name = router.route(
            "我想轻生",
            {"risk_level": "crisis", "cycle_phase": "经前期"},
        )

        self.assertEqual(agent_name, "intervention_fallback")
        self.assertIn("安全", reply)
        self.assertIn("可信任的人", reply)

    def test_agent_service_exception_uses_crisis_fallback_for_self_harm_text(self):
        from app.services.agent_service import AgentService

        class BrokenPerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                raise RuntimeError("perception unavailable")

        service = AgentService()
        service.perception = BrokenPerception()

        import asyncio

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="test",
                user_message="我想自残",
                context={},
            )
        )

        self.assertEqual(result["intent"], "intervention_fallback")
        self.assertEqual(result["state"]["risk_level"], "crisis")
        self.assertIn("可信任的人", result["message"])

    def test_agent_service_threads_memory_context_and_mode_guidance_to_router(self):
        from app.services.agent_service import AgentService

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "low", "cycle_phase": cycle_phase or "经前期"}

        class RecordingRouter:
            def __init__(self):
                self.last_state = None
                self.last_agent_mode = None

            def route(self, message: str, state: dict, agent_mode: str = "auto"):
                self.last_state = state
                self.last_agent_mode = agent_mode
                return "我记得你之前说过经前睡不好，我们先从最小的一步开始。", "support"

        service = AgentService()
        service.perception = PassivePerception()
        service.router = RecordingRouter()

        import asyncio

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="memory-thread",
                user_message="今天又有点烦",
                context={
                    "cycle_phase": "经前期",
                    "conversation_memory": {
                        "memory_context": "- 用户经前常睡不好",
                        "recent_context": "user: 我昨天说过睡不好",
                        "memory_state": {"has_memory": True, "count": 1},
                    },
                },
                agent_mode="support",
            )
        )

        self.assertEqual(result["intent"], "support")
        self.assertEqual(service.router.last_agent_mode, "support")
        self.assertIn("经前常睡不好", service.router.last_state["memory_context"])
        self.assertIn("我昨天说过睡不好", service.router.last_state["recent_context"])
        self.assertIn("共情", service.router.last_state["mode_guidance"])

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

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="timeout-test",
                user_message="我有点难过",
                context={},
                agent_mode="support",
            )
        )

        self.assertLess(result["elapsed_ms"], 150)
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

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="crisis-timeout",
                user_message="我想自残",
                context={},
                agent_mode="auto",
            )
        )

        self.assertEqual(result["intent"], "timeout_fallback")
        self.assertEqual(result["reply_status"], "timeout_fallback")
        self.assertIn("可信任的人", result["message"])

    def test_interview_copy_uses_subtle_state_assessment_language(self):
        from app.agents.interview_agent import InterviewAgent

        agent = InterviewAgent()
        messages = [SimpleNamespace(role="assistant", content=agent.start())]
        copies = [agent.start(), agent.next_turn(messages)]
        banned_terms = ["筛查", "检验", "测试", "量表", "诊断"]

        for copy in copies:
            for term in banned_terms:
                self.assertNotIn(term, copy)

    def test_interview_detects_self_harm_language_as_crisis(self):
        from app.agents.interview_agent import InterviewAgent

        agent = InterviewAgent()
        messages = [SimpleNamespace(role="user", content="我想自残")]

        self.assertTrue(agent.detect_crisis(messages))

    def test_prompt_loader_reads_prompt_template_from_prompts_directory(self):
        from app.utils.prompt_loader import load_prompt, render_prompt

        prompt = load_prompt("support_prompt.txt")

        self.assertIn("MoonCARE", prompt)
        self.assertIn("不做医疗诊断", prompt)
        rendered = render_prompt(
            "support_prompt.txt",
            cycle_phase="黄体期",
            risk_level="low",
        )
        self.assertIn("黄体期", rendered)
        self.assertIn("low", rendered)

    def test_llm_service_sends_recent_conversation_as_chat_messages(self):
        from app.agents.llm_service import LLMService

        class FakeCompletions:
            def __init__(self):
                self.last_messages = None

            def create(self, model, messages, temperature, max_tokens):
                self.last_messages = messages
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content="20elik 是刚才提到的游戏名。")
                        )
                    ]
                )

        class FakeChat:
            def __init__(self):
                self.completions = FakeCompletions()

        service = LLMService.__new__(LLMService)
        service.model = "fake-model"
        service.client = SimpleNamespace(chat=FakeChat())

        reply = service.generate_reply(
            "这是什么游戏",
            {
                "raw_system_prompt": "你需要优先使用最近对话上下文回答指代问题。",
                "conversation_messages": [
                    {"role": "assistant", "content": "可以玩 20elik。"},
                ],
            },
        )

        self.assertIn("20elik", reply)
        sent_messages = service.client.chat.completions.last_messages
        self.assertEqual(sent_messages[1]["role"], "assistant")
        self.assertIn("20elik", sent_messages[1]["content"])
        self.assertEqual(sent_messages[-1], {"role": "user", "content": "这是什么游戏"})


if __name__ == "__main__":
    unittest.main()
