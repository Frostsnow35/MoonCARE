import asyncio
import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class _FakeAgentService:
    def __init__(self):
        self.last_context = None

    async def get_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: dict,
        agent_mode: str = "auto",
    ) -> dict:
        self.last_context = context
        return {
            "message": "我在这里陪你。最近经前那几天，身体上有没有也更累或睡不好？",
            "intent": "support",
            "suggestions": [],
            "state": {"risk_level": context.get("risk_level", "medium")},
        }


class P1AssessmentLoopTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base
        from app.models.biometric import BiometricData
        from app.models.menstrual import MenstrualRecord
        from app.models.mood import MoodDiary
        from app.models.music import Music
        from app.models.conversation import Conversation
        from app.models.chat_memory import ChatMemory
        from app.models.assessment import AssessmentObservation, AssessmentSession
        from app.models.user import User

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(User(id=1, email="p1@example.com", hashed_password="x"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_orchestrator_creates_hidden_state_for_low_mood_without_screening_copy(self):
        from app.services.assessment_service import AssessmentOrchestrator

        orchestrator = AssessmentOrchestrator(self.db)

        result = orchestrator.prepare_turn(
            user_id=1,
            chat_session_id="session-low",
            user_message="我最近经前很烦躁，也有点低落",
            context={
                "sentiment_score": -0.7,
                "risk_level": "medium",
                "cycle_phase": "luteal",
            },
        )

        self.assertEqual(result.assessment_state["status"], "awaiting_answer")
        self.assertIsNotNone(result.assessment_state["current_dimension"])
        self.assertTrue(result.assessment_prompt_hint)
        for banned in ["筛查", "量表", "诊断", "测评"]:
            self.assertNotIn(banned, result.assessment_prompt_hint)

    def test_orchestrator_routes_crisis_to_handoff_without_probe(self):
        from app.services.assessment_service import AssessmentOrchestrator

        orchestrator = AssessmentOrchestrator(self.db)

        result = orchestrator.prepare_turn(
            user_id=1,
            chat_session_id="session-crisis",
            user_message="我想死，真的不想活了",
            context={"risk_level": "crisis", "sentiment_score": -1.0},
        )

        self.assertEqual(result.assessment_state["status"], "crisis_handoff")
        self.assertIsNone(result.assessment_prompt_hint)

    def test_record_answer_persists_structured_observation(self):
        from app.services.assessment_service import AssessmentOrchestrator
        from app.models.assessment import AssessmentObservation

        orchestrator = AssessmentOrchestrator(self.db)
        orchestrator.prepare_turn(
            user_id=1,
            chat_session_id="session-extract",
            user_message="我最近经前很烦躁",
            context={"risk_level": "medium", "sentiment_score": -0.5},
        )

        observation = orchestrator.record_user_answer(
            user_id=1,
            chat_session_id="session-extract",
            user_message="那几天我特别烦躁，睡不好，学习也明显受影响",
            conversation_id=None,
        )

        self.assertIsNotNone(observation)
        self.assertGreaterEqual(observation.value["irritability"], 2)
        self.assertGreaterEqual(observation.value["sleep_change"], 2)
        self.assertGreaterEqual(observation.value["study_work"], 2)

        saved = self.db.query(AssessmentObservation).one()
        self.assertEqual(saved.dimension, "mixed")
        self.assertGreater(saved.confidence, 0)

    def test_emotion_engine_negative_ratio_uses_user_conversation_scores(self):
        from app.models.conversation import Conversation
        from app.services.emotion_engine import EmotionEngine

        self.db.add_all(
            [
                Conversation(user_id=1, session_id="s", turn_number=1, role="user", content="烦", sentiment_score=-0.8),
                Conversation(user_id=1, session_id="s", turn_number=2, role="assistant", content="我在"),
                Conversation(user_id=1, session_id="s", turn_number=3, role="user", content="还好", sentiment_score=0.2),
                Conversation(user_id=1, session_id="s", turn_number=4, role="user", content="低落", sentiment_score=-0.4),
            ]
        )
        self.db.commit()

        engine = EmotionEngine(self.db)
        ratio = engine._get_negative_emotion_ratio(1, start=None, end=None)

        self.assertAlmostEqual(ratio, 2 / 3)

    def test_chat_message_response_includes_hidden_assessment_state(self):
        from app.api.v1 import chat
        from app.models.assessment import AssessmentSession

        original_get_agent_service = chat.get_agent_service
        chat.get_agent_service = lambda: _FakeAgentService()
        try:
            response = asyncio.run(
                chat.send_chat_message(
                    message="我最近经前很烦躁，睡不好",
                    user_id=1,
                    session_id="session-api",
                    cycle_phase="luteal",
                    db=self.db,
                )
            )
        finally:
            chat.get_agent_service = original_get_agent_service

        self.assertIn("assessment_state", response)
        self.assertEqual(response["assessment_state"]["status"], "awaiting_answer")
        self.assertTrue(self.db.query(AssessmentSession).filter_by(chat_session_id="session-api").first())

    def test_chat_does_not_extract_observation_until_user_answers_prior_probe(self):
        from app.api.v1 import chat
        from app.models.assessment import AssessmentObservation

        original_get_agent_service = chat.get_agent_service
        chat.get_agent_service = lambda: _FakeAgentService()
        try:
            first_response = asyncio.run(
                chat.send_chat_message(
                    message="我最近经前很烦躁，睡不好",
                    user_id=1,
                    session_id="session-two-step",
                    cycle_phase="luteal",
                    db=self.db,
                )
            )
            self.assertEqual(first_response["assessment_state"]["status"], "awaiting_answer")
            self.assertEqual(self.db.query(AssessmentObservation).count(), 0)

            second_response = asyncio.run(
                chat.send_chat_message(
                    message="会影响学习，也不太想见人",
                    user_id=1,
                    session_id="session-two-step",
                    cycle_phase="luteal",
                    db=self.db,
                )
            )
        finally:
            chat.get_agent_service = original_get_agent_service

        self.assertIn(second_response["assessment_state"]["status"], {"awaiting_answer", "completed", "cooldown"})
        self.assertEqual(self.db.query(AssessmentObservation).count(), 1)

    def test_chat_message_updates_memory_state_for_safe_user_preference(self):
        from app.api.v1 import chat
        from app.models.chat_memory import ChatMemory
        from app.models.conversation import Conversation

        fake_agent_service = _FakeAgentService()
        original_get_agent_service = chat.get_agent_service
        chat.get_agent_service = lambda: fake_agent_service
        try:
            response = asyncio.run(
                chat.send_chat_message(
                    message="我喜欢晚上听轻音乐，别一下子给我很多建议",
                    user_id=1,
                    session_id="session-memory",
                    cycle_phase="luteal",
                    db=self.db,
                )
            )
        finally:
            chat.get_agent_service = original_get_agent_service

        self.assertIn("memory_state", response)
        self.assertTrue(response["memory_state"]["updated"])
        self.assertGreaterEqual(self.db.query(ChatMemory).filter_by(user_id=1).count(), 2)
        self.assertIn("conversation_memory", fake_agent_service.last_context)
        self.assertFalse(fake_agent_service.last_context["conversation_memory"]["memory_state"]["has_memory"])
        assistant_turn = (
            self.db.query(Conversation)
            .filter(Conversation.session_id == "session-memory", Conversation.role == "assistant")
            .one()
        )
        self.assertEqual(assistant_turn.message_meta["reply_status"], "ok")
        self.assertIn("assessment_snapshot", assistant_turn.message_meta)
        self.assertIn("memory_snapshot", assistant_turn.message_meta)

    def test_chat_history_returns_assistant_message_meta(self):
        from app.api.v1 import chat
        from app.models.conversation import Conversation

        self.db.add_all(
            [
                Conversation(
                    user_id=1,
                    session_id="session-history",
                    turn_number=1,
                    role="user",
                    content="我最近经前有点烦躁",
                ),
                Conversation(
                    user_id=1,
                    session_id="session-history",
                    turn_number=2,
                    role="assistant",
                    content="我在这里陪你慢慢说。",
                    message_meta={
                        "suggestions": ["继续说一点"],
                        "actions": [{"action": "open_diary", "label": "写日记"}],
                        "reply_status": "ok",
                        "elapsed_ms": 23,
                        "assessment_snapshot": {"status": "awaiting_answer"},
                        "memory_snapshot": {"updated": True},
                    },
                ),
            ]
        )
        self.db.commit()

        response = asyncio.run(
            chat.get_chat_history(
                session_id="session-history",
                user_id=1,
                db=self.db,
            )
        )

        assistant_turn = response.turns[1]
        self.assertEqual(assistant_turn["role"], "assistant")
        self.assertEqual(assistant_turn["reply_status"], "ok")
        self.assertEqual(assistant_turn["elapsed_ms"], 23)
        self.assertEqual(assistant_turn["assessment_state"]["status"], "awaiting_answer")
        self.assertTrue(assistant_turn["memory_state"]["updated"])
        self.assertEqual(assistant_turn["suggestions"], ["继续说一点"])
        self.assertEqual(assistant_turn["actions"][0]["action"], "open_diary")


if __name__ == "__main__":
    unittest.main()
