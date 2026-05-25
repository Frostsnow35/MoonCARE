import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class ChatMemoryServiceTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base
        from app.models.assessment import AssessmentObservation, AssessmentSession
        from app.models.biometric import BiometricData
        from app.models.chat_memory import ChatMemory
        from app.models.conversation import Conversation
        from app.models.menstrual import MenstrualRecord
        from app.models.mood import MoodDiary
        from app.models.music import Music
        from app.models.user import User

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(User(id=1, email="memory@example.com", hashed_password="x"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_capture_user_preference_and_build_memory_context(self):
        from app.models.chat_memory import ChatMemory
        from app.services.chat_memory_service import ChatMemoryService

        service = ChatMemoryService(self.db)

        result = service.capture_user_message(
            user_id=1,
            conversation_id=None,
            message="我喜欢晚上听轻音乐，别一下子给我很多建议",
            context={"sentiment_score": 0.1},
            is_sensitive=False,
        )

        self.assertTrue(result["updated"])
        memories = self.db.query(ChatMemory).filter_by(user_id=1).all()
        self.assertGreaterEqual(len(memories), 2)

        prompt_context = service.build_prompt_context(user_id=1, session_id="session-a")
        self.assertIn("晚上听轻音乐", prompt_context["memory_context"])
        self.assertIn("少量建议", prompt_context["memory_context"])
        self.assertTrue(prompt_context["memory_state"]["has_memory"])

    def test_capture_premenstrual_trait_without_diagnostic_language(self):
        from app.services.chat_memory_service import ChatMemoryService

        service = ChatMemoryService(self.db)

        service.capture_user_message(
            user_id=1,
            conversation_id=None,
            message="我经前总是睡不好，学习效率也会明显下降",
            context={"sentiment_score": -0.6, "cycle_phase": "luteal"},
            is_sensitive=False,
        )

        prompt_context = service.build_prompt_context(user_id=1, session_id="session-b")
        self.assertIn("经前", prompt_context["memory_context"])
        self.assertIn("睡不好", prompt_context["memory_context"])
        self.assertNotIn("诊断", prompt_context["memory_context"])
        self.assertNotIn("筛查", prompt_context["memory_context"])

    def test_crisis_message_is_not_saved_as_regular_memory(self):
        from app.models.chat_memory import ChatMemory
        from app.services.chat_memory_service import ChatMemoryService

        service = ChatMemoryService(self.db)

        result = service.capture_user_message(
            user_id=1,
            conversation_id=None,
            message="我想自残，也喜欢晚上听音乐",
            context={"sentiment_score": -1.0},
            is_sensitive=True,
        )

        self.assertFalse(result["updated"])
        self.assertEqual(self.db.query(ChatMemory).filter_by(user_id=1).count(), 0)

    def test_recent_context_uses_existing_conversation_turns(self):
        from app.models.conversation import Conversation
        from app.services.chat_memory_service import ChatMemoryService

        self.db.add_all(
            [
                Conversation(user_id=1, session_id="session-c", turn_number=1, role="user", content="我今天很烦"),
                Conversation(user_id=1, session_id="session-c", turn_number=2, role="assistant", content="我在听"),
                Conversation(user_id=1, session_id="session-c", turn_number=3, role="user", content="主要是睡不好"),
            ]
        )
        self.db.commit()

        service = ChatMemoryService(self.db)
        prompt_context = service.build_prompt_context(user_id=1, session_id="session-c", recent_turn_limit=2)

        self.assertNotIn("我今天很烦", prompt_context["recent_context"])
        self.assertIn("assistant: 我在听", prompt_context["recent_context"])
        self.assertIn("user: 主要是睡不好", prompt_context["recent_context"])

    def test_retrieval_context_resolves_deictic_follow_up_about_prior_game(self):
        from app.models.conversation import Conversation
        from app.services.chat_memory_service import ChatMemoryService

        self.db.add_all(
            [
                Conversation(user_id=1, session_id="session-game", turn_number=1, role="user", content="我们玩什么？"),
                Conversation(user_id=1, session_id="session-game", turn_number=2, role="assistant", content="可以玩 20elik，或者一起做轻松的家庭游戏。"),
                Conversation(user_id=1, session_id="session-game", turn_number=3, role="user", content="还有别的吗？"),
                Conversation(user_id=1, session_id="session-game", turn_number=4, role="assistant", content="也可以玩猜词或抽卡聊天。"),
            ]
        )
        self.db.commit()

        service = ChatMemoryService(self.db)
        prompt_context = service.build_prompt_context(
            user_id=1,
            session_id="session-game",
            query_message="这是什么游戏",
            recent_turn_limit=1,
        )

        self.assertIn("20elik", prompt_context["retrieved_context"])
        self.assertGreaterEqual(prompt_context["memory_state"]["retrieved_turns"], 1)
        self.assertTrue(prompt_context["memory_state"]["needs_context_resolution"])

    def test_conversation_messages_are_prompt_ready_for_llm(self):
        from app.models.conversation import Conversation
        from app.services.chat_memory_service import ChatMemoryService

        self.db.add_all(
            [
                Conversation(user_id=1, session_id="session-llm", turn_number=1, role="user", content="我们玩什么？"),
                Conversation(user_id=1, session_id="session-llm", turn_number=2, role="assistant", content="可以玩 20elik。"),
            ]
        )
        self.db.commit()

        service = ChatMemoryService(self.db)
        prompt_context = service.build_prompt_context(
            user_id=1,
            session_id="session-llm",
            query_message="这是什么游戏",
        )

        self.assertEqual(
            prompt_context["conversation_messages"],
            [
                {"role": "user", "content": "我们玩什么？"},
                {"role": "assistant", "content": "可以玩 20elik。"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
