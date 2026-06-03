import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class ChatAgentQualityTests(unittest.TestCase):
    def test_short_ambiguous_distress_reply_keeps_feeling_open(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我有点难受",
            {"cycle_phase": "经前期", "risk_level": "medium"},
        )

        self.assertTrue(reply)
        for forbidden in ["低落", "压下去", "解释清楚", "经前", "经期", "诊断"]:
            self.assertNotIn(forbidden, reply)
        self.assertTrue(any(marker in reply for marker in ["啦", "呀", "呢", "🌷", "💗", "🫶"]))
        self.assertIn("心里", reply)
        self.assertIn("身体", reply)
        self.assertNotIn("更像什么感觉", reply)
        self.assertNotIn("被人惹到了、身体不舒服，还是事情太多", reply)

    def test_clear_body_discomfort_comforts_and_guides_without_more_questioning(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我来月经了，头晕，小腹也很痛",
            {"cycle_phase": "经期", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("头晕", reply)
        self.assertTrue(any(marker in reply for marker in ["坐", "躺", "热敷", "温水", "休息"]))
        for forbidden in ["消耗掉一点", "被看见", "待一会儿", "愿意", "说说"]:
            self.assertNotIn(forbidden, reply)

    def test_clear_emotional_context_gets_support_not_interview_question(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我因为和男朋友吵架很委屈",
            {"cycle_phase": "未知", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("男朋友", reply)
        self.assertIn("委屈", reply)
        self.assertTrue(any(marker in reply for marker in ["抱", "缓", "陪", "站在你这边"]))
        for forbidden in ["愿意说说", "更像什么感觉", "什么样的难受", "待一会儿"]:
            self.assertNotIn(forbidden, reply)

    def test_reply_repair_removes_repeated_sentence(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.repair_reply(
            "我有点难受",
            "我听到啦，你现在心里/身体不太舒服。我听到啦，你现在心里/身体不太舒服。"
            "这种感觉可以先在这里待一会儿。",
            {"risk_level": "medium"},
        )

        self.assertEqual(reply.count("我听到啦，你现在心里/身体不太舒服"), 1)

    def test_body_discomfort_defaults_to_witnessing_before_advice(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我来月经了，身体不舒服",
            {"cycle_phase": "经期", "risk_level": "low"},
        )

        self.assertTrue(reply)
        self.assertIn("身体不舒服", reply)
        self.assertIn("我会", reply)
        self.assertTrue(any(marker in reply for marker in ["啦", "呀", "呢", "🫶", "💗", "🌷"]))
        self.assertNotIn("消耗掉一点", reply)
        self.assertNotIn("被看见", reply)
        for forbidden in [
            "尤其是来月经或经期前后",
            "蜷起来",
            "出血异常",
            "专业医生",
            "仅供参考",
            "一阵一阵",
            "持续的坠胀",
        ]:
            self.assertNotIn(forbidden, reply)

    def test_body_pain_follow_up_uses_recent_context_instead_of_repeating(self):
        from app.services.response_quality_service import ResponseQualityGuard

        guard = ResponseQualityGuard()
        reply = guard.direct_reply_if_applicable(
            "我感觉真的很痛",
            {
                "cycle_phase": "经期",
                "risk_level": "low",
                "support_context": {"body_signals": ["pain"], "menstrual_related": True},
                "conversation_messages": [
                    {"role": "user", "content": "我来月经了，身体不舒服"},
                    {
                        "role": "assistant",
                        "content": "我听到啦，来月经的时候身体不舒服真的会把人消耗掉一点。我们可以先只陪它待一会儿，让这份不舒服被看见。",
                    },
                ],
            },
        )

        self.assertTrue(reply)
        self.assertIn("刚才", reply)
        self.assertIn("来月经", reply)
        self.assertIn("真的很痛", reply)
        self.assertNotIn("来月经的时候身体不舒服真的会把人消耗掉一点", reply)
        self.assertNotIn("愿意", reply)
        self.assertNotIn("说说", reply)


class KnowledgeAgentLocalRagTests(unittest.TestCase):
    def test_knowledge_agent_loads_local_cards_without_llm_provider(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        self.assertGreater(len(agent.knowledge), 0)
        self.assertIsNone(agent.llm)

    def test_knowledge_agent_answers_from_local_card_when_llm_unavailable(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond("为什么经前会情绪波动？", {})

        self.assertIn("经前", reply)
        self.assertIn("仅供参考", reply)
        self.assertNotIn("暂时没有相关信息", reply)

    def test_knowledge_agent_fallback_answers_the_specific_symptom(self):
        from app.agents import knowledge_agent as knowledge_module

        with patch.object(knowledge_module, "LLMService", side_effect=ValueError("missing api key")):
            agent = knowledge_module.KnowledgeAgent()

        reply = agent.respond("经期为什么会头晕？", {})

        self.assertIn("头晕", reply)
        self.assertIn("经期", reply)
        self.assertIn("仅供参考", reply)
        self.assertNotIn("情绪突然变化", reply)
        self.assertNotIn("我帮你一起梳理规律", reply)


class StreamingFallbackTests(unittest.TestCase):
    def test_streaming_support_second_turn_uses_soft_fallback_without_error_when_llm_unavailable(self):
        import asyncio
        from app.services import agent_service as agent_module

        async def collect_chunks():
            service = agent_module.AgentService()
            with patch.object(agent_module, "LLMService", side_effect=ValueError("missing api key")):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="same-session",
                        user_message="还是有点堵",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")
        end_chunks = [chunk for chunk in chunks if chunk.get("type") == "end"]

        self.assertTrue(token_text)
        self.assertTrue(end_chunks)
        self.assertNotIn("error", end_chunks[-1])

    def test_streaming_support_uses_timeout_fallback_when_llm_stream_is_empty(self):
        import asyncio
        from app.services import agent_service as agent_module

        class EmptyStreamLLM:
            async def async_streaming_generate_reply(self, user_message, context):
                if False:
                    yield {"token": ""}

        async def collect_chunks():
            service = agent_module.AgentService()
            with patch.object(service, "_get_llm_service", return_value=EmptyStreamLLM()):
                return [
                    chunk
                    async for chunk in service.get_streaming_response(
                        user_id=1,
                        session_id="empty-stream-session",
                        user_message="hello",
                        context={"conversation_memory": {"conversation_messages": []}},
                        agent_mode="support",
                        pre_built_state={"risk_level": "low", "message": "hello"},
                    )
                ]

        chunks = asyncio.run(collect_chunks())
        token_text = "".join(chunk.get("token", "") for chunk in chunks if chunk.get("type") == "token")
        end_chunks = [chunk for chunk in chunks if chunk.get("type") == "end"]

        self.assertTrue(token_text)
        self.assertTrue(end_chunks)
        self.assertEqual(end_chunks[-1].get("full_response"), token_text)


class SemanticCacheCompatibilityTests(unittest.TestCase):
    def test_dummy_cache_matches_agent_service_contract(self):
        from app.services.semantic_cache_service import DummySemanticCache

        cache = DummySemanticCache()

        self.assertIsNone(cache.get_cached_response("hello"))
        self.assertIsNone(cache.set_cached_response("hello", "reply", ttl_hours=1))


class LLMServiceTokenBudgetTests(unittest.TestCase):
    def test_generate_reply_uses_configured_max_response_tokens(self):
        from app.agents.llm_service import LLMService
        from app.config import settings

        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                message = SimpleNamespace(content="我是她语 MoonCARE 的情绪陪伴者。")
                choice = SimpleNamespace(message=message)
                return SimpleNamespace(choices=[choice])

        service = object.__new__(LLMService)
        service.model = "stepfun-ai/step-3.5-flash"
        service.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

        reply = service.generate_reply("你是谁", {"risk_level": "low"})

        self.assertIn("MoonCARE", reply)
        self.assertEqual(calls[-1]["max_tokens"], settings.MAX_RESPONSE_TOKENS)


class AgentServiceQualityGuardTests(unittest.TestCase):
    def test_get_response_uses_quality_guard_before_llm_for_body_discomfort(self):
        import asyncio
        from app.services.agent_service import AgentService

        async def run():
            service = AgentService()
            message = "\u6211\u6765\u6708\u7ecf\u4e86\uff0c\u8eab\u4f53\u4e0d\u8212\u670d"
            with patch.object(
                service,
                "_route_with_deadline",
                side_effect=AssertionError("router should not be called"),
            ):
                return await service.get_response(
                    user_id=1,
                    session_id="quality-guard-fast",
                    user_message=message,
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="auto",
                )

        response = asyncio.run(run())

        self.assertEqual(response["reply_status"], "ok")
        self.assertEqual(response["intent"], "support_quality_guard")
        self.assertTrue(response.get("suppress_assessment_prompt"))
        self.assertIn("\u8eab\u4f53\u4e0d\u8212\u670d", response["message"])

    def test_timeout_fallback_is_contextual_not_fixed_template(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        reply = service._timeout_fallback(
            "我今天被老板批评了，心里乱成一团",
            {"risk_level": "low", "agent_mode": "support"},
        )

        self.assertIn("老板批评", reply)
        self.assertNotIn("最明显的那一点", reply)
        self.assertNotIn("刚才没有顺利接上", reply)
        self.assertNotIn("你可以继续说下一句", reply)

    def test_action_request_timeout_fallback_gives_concrete_next_steps(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我因为和男朋友吵架很委屈"},
                {"role": "assistant", "content": "我听到啦，和男朋友吵架后的委屈真的会很扎心。"},
            ],
        }
        reply = service._timeout_fallback("我该怎么做", state)

        for marker in ["先", "写", "等"]:
            self.assertIn(marker, reply)
        for forbidden in ["我跟上了", "轻飘飘", "继续往下放", "你可以继续说"]:
            self.assertNotIn(forbidden, reply)

    def test_action_request_with_body_context_gives_body_care_steps(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我来月经了，头晕，小腹也很痛"},
                {"role": "assistant", "content": "先坐下或躺一会儿，能热敷就轻轻热敷小腹。"},
            ],
        }
        reply = service._soft_error_fallback("我该怎么做", state)

        self.assertIn("热敷", reply)
        self.assertIn("温水", reply)
        self.assertIn("医生", reply)
        self.assertNotIn("我跟上了", reply)

    def test_action_request_uses_latest_visible_context_before_stale_health_memory(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我因为和男朋友吵架很委屈"},
                {"role": "assistant", "content": "我听到啦，和男朋友吵架后的委屈真的会很扎心。"},
            ],
            "health_context": "用户之前提到来月经、小腹痛、头晕。",
            "memory_context": "历史记忆：经期身体不舒服。",
        }
        reply = service._timeout_fallback("我该怎么做", state)

        self.assertIn("争论", reply)
        self.assertIn("写", reply)
        self.assertNotIn("热敷", reply)
        self.assertNotIn("小腹", reply)

    def test_action_request_repairs_vague_support_reply(self):
        from app.services.agent_service import AgentService

        service = AgentService()
        state = {
            "risk_level": "low",
            "agent_mode": "support",
            "conversation_messages": [
                {"role": "user", "content": "我最近真的很烦躁，不知道该怎么办"},
            ],
        }
        reply = service._repair_reply_quality(
            "我该怎么做",
            "我在。你可以继续说，我会先跟着你现在最明显的感受。",
            state,
        )

        self.assertIn("先", reply)
        self.assertTrue(any(marker in reply for marker in ["写", "离开", "放下", "暂停"]))
        self.assertNotIn("你可以继续说", reply)

    def test_knowledge_response_suppresses_hidden_assessment_prompt(self):
        import asyncio
        from app.services.agent_service import AgentService

        async def run():
            service = AgentService()
            with patch.object(
                service,
                "_route_with_deadline",
                return_value=("经期头晕可能和疼痛、睡眠、出血量变化有关。以上仅供参考。", "knowledge"),
            ):
                return await service.get_response(
                    user_id=1,
                    session_id="knowledge-no-probe",
                    user_message="经期为什么会头晕？",
                    context={"conversation_memory": {"conversation_messages": []}},
                    agent_mode="knowledge",
                )

        response = asyncio.run(run())

        self.assertTrue(response.get("suppress_assessment_prompt"))
        self.assertEqual(response["intent"], "knowledge")

    def test_frontend_failure_copy_does_not_expose_template_failure(self):
        chat_view = (BACKEND_ROOT.parent / "frontend" / "src" / "views" / "Chat.vue").read_text(encoding="utf-8")

        self.assertNotIn("刚才没有顺利接上完整回复", chat_view)
        self.assertNotIn("刚才没有顺利接上。你可以直接继续说一句", chat_view)


class AssessmentTimingTests(unittest.TestCase):
    def test_generic_first_distress_does_not_trigger_menstrual_probe(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.database import Base
        from app.models.assessment import AssessmentObservation, AssessmentSession  # noqa: F401
        from app.models.auth import EmailVerificationCode  # noqa: F401
        from app.models.biometric import BiometricData  # noqa: F401
        from app.models.chat_memory import ChatMemory  # noqa: F401
        from app.models.conversation import Conversation  # noqa: F401
        from app.models.menstrual import MenstrualRecord  # noqa: F401
        from app.models.mood import MoodDiary  # noqa: F401
        from app.models.music import Music  # noqa: F401
        from app.models.user import User  # noqa: F401
        from app.services.assessment_service import AssessmentOrchestrator

        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            result = AssessmentOrchestrator(db).prepare_turn(
                user_id=1,
                chat_session_id="generic-first-distress",
                user_message="我有点难受",
                context={"sentiment_score": -0.8, "risk_level": "medium"},
            )
        finally:
            db.close()

        self.assertIsNone(result.assessment_prompt_hint)


if __name__ == "__main__":
    unittest.main()
