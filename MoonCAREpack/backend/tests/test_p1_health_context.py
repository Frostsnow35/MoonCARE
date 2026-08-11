import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class P1HealthContextTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base
        from app.models.assessment import AssessmentObservation, AssessmentSession  # noqa: F401
        from app.models.biometric import BiometricData  # noqa: F401
        from app.models.chat_memory import ChatMemory  # noqa: F401
        from app.models.conversation import Conversation  # noqa: F401
        from app.models.menstrual import MenstrualRecord  # noqa: F401
        from app.models.mood import MoodDiary  # noqa: F401
        from app.models.music import Music  # noqa: F401
        from app.models.user import User

        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.db.add(User(id=1, email="context-owner@example.com", hashed_password="x"))
        self.db.add(User(id=2, email="context-other@example.com", hashed_password="x"))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_product_memory_context_includes_only_current_user_cycle_and_diary(self):
        from app.models.menstrual import MenstrualRecord
        from app.models.mood import MoodDiary
        from app.services.product_memory_service import ProductMemoryService

        today = date.today()
        self.db.add(
            MenstrualRecord(
                user_id=1,
                cycle_number=1,
                start_date=today - timedelta(days=2),
                end_date=today,
                flow_intensity=3,
                symptoms='["cramps", "fatigue"]',
                notes="owner cycle note",
            )
        )
        self.db.add(
            MoodDiary(
                user_id=1,
                date=datetime.now() - timedelta(hours=2),
                input_type="text",
                original_text="今天小腹痛，也有点烦。",
                mood_level=3.0,
                emotion_tags='["焦虑"]',
                keywords='["小腹痛", "烦"]',
            )
        )
        self.db.add(
            MenstrualRecord(
                user_id=2,
                cycle_number=1,
                start_date=today - timedelta(days=10),
                flow_intensity=5,
                notes="other private cycle",
            )
        )
        self.db.add(
            MoodDiary(
                user_id=2,
                date=datetime.now() - timedelta(hours=1),
                input_type="text",
                original_text="other private diary",
                mood_level=9.0,
                keywords='["other private keyword"]',
            )
        )
        self.db.commit()

        context = ProductMemoryService(self.db, enable_awareness=False).build_prompt_context(
            user_id=1,
            session_id="health-context-session",
            query_message="我今天身体不舒服",
        )

        self.assertIn("health_context", context)
        self.assertIn("周期", context["health_context"])
        self.assertIn(str(today - timedelta(days=2)), context["health_context"])
        self.assertIn("小腹痛", context["health_context"])
        self.assertIn("烦", context["health_context"])
        self.assertNotIn("other private", context["health_context"])
        self.assertTrue(context["memory_state"]["health_context_available"])

    def test_agent_service_threads_health_context_to_router_state(self):
        from app.services.agent_service import AgentService

        class PassivePerception:
            def analyze(self, message: str, cycle_phase=None, sensor_data=None):
                return {"risk_level": "low", "cycle_phase": cycle_phase or "未知"}

        class RecordingRouter:
            def __init__(self):
                self.last_state = None

            def route(self, message: str, state: dict, agent_mode: str = "auto"):
                self.last_state = state
                return "我看到你最近记录过小腹痛，我们先听听身体现在最明显的感觉。", "support"

        service = AgentService()
        service.perception = PassivePerception()
        service.router = RecordingRouter()

        import asyncio

        result = asyncio.run(
            service.get_response(
                user_id=1,
                session_id="health-router-session",
                user_message="我今天有点不舒服",
                context={
                    "cycle_phase": None,
                    "conversation_memory": {
                        "memory_context": "暂无可用长期记忆。",
                        "recent_context": "暂无最近对话。",
                        "health_context": "- 周期：当前可能在经期第3天。\n- 近日情绪日记：小腹痛、烦。",
                        "memory_state": {"has_memory": False, "count": 0},
                    },
                },
            )
        )

        self.assertEqual(result["intent"], "support")
        self.assertIn("小腹痛", service.router.last_state["health_context"])
        self.assertIn("经期第3天", service.router.last_state["health_context"])


if __name__ == "__main__":
    unittest.main()
