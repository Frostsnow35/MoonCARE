import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class _FakeAgentService:
    async def get_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: dict,
        agent_mode: str = "auto",
    ) -> dict:
        return {
            "message": "我在这里陪你。",
            "intent": "support",
            "suggestions": [],
            "actions": [],
            "state": {"risk_level": "low"},
            "reply_status": "ok",
            "elapsed_ms": 1,
        }

    async def get_streaming_response(
        self,
        user_id: int,
        session_id: str,
        user_message: str,
        context: dict,
        agent_mode: str = "auto",
    ):
        yield {"type": "start", "risk_level": "low", "agent_name": "support"}
        yield {"type": "token", "token": "我在", "is_final": False}
        yield {
            "type": "end",
            "full_response": "我在这里陪你。",
            "actions": [],
            "elapsed_ms": 1,
        }


class P0ChatWebSocketAuthTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base, get_db
        from app.main import app

        # Import every model registered by app.main so relationship metadata is complete.
        from app.models.assessment import AssessmentObservation, AssessmentSession  # noqa: F401
        from app.models.auth import EmailVerificationCode  # noqa: F401
        from app.models.biometric import BiometricData  # noqa: F401
        from app.models.chat_memory import ChatMemory  # noqa: F401
        from app.models.conversation import Conversation  # noqa: F401
        from app.models.menstrual import MenstrualRecord  # noqa: F401
        from app.models.mood import MoodDiary  # noqa: F401
        from app.models.music import Music  # noqa: F401
        from app.models.user import User  # noqa: F401

        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.app = app
        self.client = TestClient(app)
        self.addCleanup(lambda: app.dependency_overrides.clear())

        import app.api.v1.chat as chat_module

        self.chat_module = chat_module
        self.original_session_local = chat_module.SessionLocal
        self.original_get_agent_service = chat_module.get_agent_service
        chat_module.SessionLocal = self.SessionLocal
        chat_module.get_agent_service = lambda: _FakeAgentService()
        self.addCleanup(self._restore_chat_module)

    def _restore_chat_module(self):
        self.chat_module.SessionLocal = self.original_session_local
        self.chat_module.get_agent_service = self.original_get_agent_service

    def _create_user(self, email: str) -> tuple[int, str, dict[str, str]]:
        from app.api.v1.auth import create_access_token, hash_password
        from app.models.user import User

        db = self.SessionLocal()
        try:
            user = User(
                email=email,
                hashed_password=hash_password("Strongpass123"),
                nickname=email.split("@", 1)[0],
                is_email_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_access_token({"sub": str(user.id), "email": user.email})
            return user.id, token, {"Authorization": f"Bearer {token}"}
        finally:
            db.close()

    def test_websocket_without_token_is_rejected(self):
        with self.assertRaises(WebSocketDisconnect) as raised:
            with self.client.websocket_connect("/api/v1/chat/ws/1"):
                pass

        self.assertEqual(raised.exception.code, 1008)

    def test_websocket_uses_token_identity_not_path_user_id(self):
        from app.models.conversation import Conversation

        path_user_id, _path_user_token, _path_user_headers = self._create_user("path@example.com")
        token_user_id, token, _token_user_headers = self._create_user("token@example.com")

        with self.client.websocket_connect(f"/api/v1/chat/ws/{path_user_id}?token={token}") as websocket:
            session_message = websocket.receive_json()
            self.assertEqual(session_message["type"], "session")
            session_id = session_message["session_id"]

            websocket.send_json({"message": "今天有点烦", "agent_mode": "support"})
            assistant_message = websocket.receive_json()
            self.assertEqual(assistant_message["type"], "assistant")

        db = self.SessionLocal()
        try:
            path_user_messages = db.query(Conversation).filter(
                Conversation.user_id == path_user_id,
                Conversation.session_id == session_id,
            ).count()
            token_user_messages = db.query(Conversation).filter(
                Conversation.user_id == token_user_id,
                Conversation.session_id == session_id,
            ).count()
            self.assertEqual(path_user_messages, 0)
            self.assertEqual(token_user_messages, 2)
        finally:
            db.close()

    def test_websocket_accepts_two_messages_in_same_session(self):
        from app.models.conversation import Conversation

        user_id, token, _headers = self._create_user("ws-two-turns@example.com")

        with self.client.websocket_connect(f"/api/v1/chat/ws?token={token}") as websocket:
            session_message = websocket.receive_json()
            session_id = session_message["session_id"]

            websocket.send_json({"message": "我有点难受", "agent_mode": "support"})
            first_reply = websocket.receive_json()
            self.assertEqual(first_reply["type"], "assistant")

            websocket.send_json({"message": "还是有点堵", "agent_mode": "support"})
            second_reply = websocket.receive_json()
            self.assertEqual(second_reply["type"], "assistant")

        db = self.SessionLocal()
        try:
            saved_messages = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            ).order_by(Conversation.turn_number).all()
            self.assertEqual(len(saved_messages), 4)
            self.assertEqual([message.role for message in saved_messages], ["user", "assistant", "user", "assistant"])
        finally:
            db.close()

    def test_rest_accepts_two_messages_in_same_session(self):
        from app.models.conversation import Conversation

        user_id, _token, headers = self._create_user("rest-two-turns@example.com")

        first_response = self.client.post(
            "/api/v1/chat/message",
            data={"message": "我有点难受", "agent_mode": "support"},
            headers=headers,
        )
        self.assertEqual(first_response.status_code, 200)
        session_id = first_response.json()["session_id"]

        second_response = self.client.post(
            "/api/v1/chat/message",
            data={"message": "还是有点堵", "session_id": session_id, "agent_mode": "support"},
            headers=headers,
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["session_id"], session_id)

        db = self.SessionLocal()
        try:
            saved_count = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            ).count()
            self.assertEqual(saved_count, 4)
        finally:
            db.close()

    def test_stream_accepts_two_messages_in_same_session(self):
        from app.models.conversation import Conversation

        user_id, _token, headers = self._create_user("stream-two-turns@example.com")

        first_response = self.client.post(
            "/api/v1/chat/stream",
            data={"message": "我有点难受", "agent_mode": "support"},
            headers=headers,
        )
        self.assertEqual(first_response.status_code, 200)
        self.assertIn("session_id", first_response.text)
        session_id = first_response.text.split('"session_id": "')[1].split('"', 1)[0]

        second_response = self.client.post(
            "/api/v1/chat/stream",
            data={"message": "还是有点堵", "session_id": session_id, "agent_mode": "support"},
            headers=headers,
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertIn(session_id, second_response.text)

        db = self.SessionLocal()
        try:
            saved_count = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.session_id == session_id,
            ).count()
            self.assertEqual(saved_count, 4)
        finally:
            db.close()

    def test_rest_and_stream_reject_session_owned_by_another_user(self):
        from app.models.conversation import Conversation

        owner_id, _owner_token, _owner_headers = self._create_user("session-owner@example.com")
        _other_id, _other_token, other_headers = self._create_user("session-other@example.com")
        session_id = "owner-session"

        db = self.SessionLocal()
        try:
            db.add(
                Conversation(
                    user_id=owner_id,
                    session_id=session_id,
                    turn_number=1,
                    role="user",
                    content="owner message",
                )
            )
            db.commit()
        finally:
            db.close()

        rest_response = self.client.post(
            "/api/v1/chat/message",
            data={"message": "try hijack", "session_id": session_id},
            headers=other_headers,
        )
        self.assertEqual(rest_response.status_code, 404)

        stream_response = self.client.post(
            "/api/v1/chat/stream",
            data={"message": "try hijack", "session_id": session_id},
            headers=other_headers,
        )
        self.assertEqual(stream_response.status_code, 404)

        db = self.SessionLocal()
        try:
            total_owner_session_messages = db.query(Conversation).filter(
                Conversation.session_id == session_id,
            ).count()
            self.assertEqual(total_owner_session_messages, 1)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
