import sys
import unittest
from pathlib import Path
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
        self.assertIn("愿意说说", reply)
        self.assertNotIn("被人惹到了、身体不舒服，还是事情太多", reply)

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
        for forbidden in [
            "尤其是来月经或经期前后",
            "热敷",
            "温水",
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
        self.assertNotIn("热敷", reply)
        self.assertNotIn("温水", reply)


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


class SemanticCacheCompatibilityTests(unittest.TestCase):
    def test_dummy_cache_matches_agent_service_contract(self):
        from app.services.semantic_cache_service import DummySemanticCache

        cache = DummySemanticCache()

        self.assertIsNone(cache.get_cached_response("hello"))
        self.assertIsNone(cache.set_cached_response("hello", "reply", ttl_hours=1))


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
