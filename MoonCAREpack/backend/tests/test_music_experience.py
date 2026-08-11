import sys
import unittest
from pathlib import Path
import shutil
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class MusicExperienceTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base, get_db
        from app.main import app

        from app.models.auth import EmailVerificationCode  # noqa: F401
        from app.models.biometric import BiometricData  # noqa: F401
        from app.models.chat_memory import ChatMemory  # noqa: F401
        from app.models.conversation import Conversation  # noqa: F401
        from app.models.menstrual import MenstrualRecord  # noqa: F401
        from app.models.mood import MoodDiary  # noqa: F401
        from app.models.music import Music, MusicFeedback  # noqa: F401
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
        self.temp_path = BACKEND_ROOT.parent / ".test_tmp_music" / uuid.uuid4().hex
        self.temp_path.mkdir(parents=True, exist_ok=True)

        import app.api.v1.music as music_api

        self.original_music_dir = music_api.MUSIC_DIR
        music_api.MUSIC_DIR = self.temp_path

        def cleanup():
            app.dependency_overrides.clear()
            music_api.MUSIC_DIR = self.original_music_dir
            shutil.rmtree(self.temp_path, ignore_errors=True)

        self.addCleanup(cleanup)

    def _create_user(self) -> dict[str, str]:
        from app.api.v1.auth import create_access_token, hash_password
        from app.models.user import User

        db = self.SessionLocal()
        try:
            user = User(
                email="music-user@example.com",
                hashed_password=hash_password("Strongpass123"),
                nickname="Music User",
                is_email_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            token = create_access_token({"sub": str(user.id), "email": user.email})
            return {"Authorization": f"Bearer {token}"}
        finally:
            db.close()

    def test_recommendation_returns_simple_music_payload(self):
        from app.models.music import Music

        headers = self._create_user()
        db = self.SessionLocal()
        try:
            db.add(
                Music(
                    title="Clear Waters",
                    artist="MoonCARE",
                    url="https://example.com/clear.mp3",
                    duration=180,
                    mood_tags=["calm", "anxiety"],
                    emotion_category="anxiety",
                    is_active=1,
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            "/api/v1/music/recommend?emotion_category=anxiety",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["current_emotion"], "anxiety")
        self.assertTrue(body["recommended_songs"])
        self.assertEqual(body["recommended_songs"][0]["title"], "Clear Waters")
        self.assertIn("仅供参考", body["recommendation_context"]["safety_note"])

    def test_music_feedback_requires_auth_and_persists_current_user(self):
        from app.models.music import MusicFeedback

        unauthenticated = self.client.post(
            "/api/v1/music/feedback",
            json={"music_id": 1001, "music_title": "Forest", "action": "liked"},
        )
        self.assertEqual(unauthenticated.status_code, 401)

        headers = self._create_user()
        response = self.client.post(
            "/api/v1/music/feedback",
            headers=headers,
            json={
                "music_id": 1001,
                "music_title": "Forest",
                "action": "play_failed",
                "emotion_category": "calm",
                "source": "local",
                "note": "audio error",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["action"], "play_failed")

        db = self.SessionLocal()
        try:
            feedback = db.query(MusicFeedback).one()
            self.assertEqual(feedback.music_title, "Forest")
            self.assertEqual(feedback.action, "play_failed")
            self.assertEqual(feedback.source, "local")
        finally:
            db.close()

    def test_music_upload_requires_auth_and_persists_file_and_record(self):
        from app.models.music import Music

        unauthenticated = self.client.post(
            "/api/v1/music/upload",
            files={"file": ("song.mp3", b"fake mp3 bytes", "audio/mpeg")},
        )
        self.assertEqual(unauthenticated.status_code, 401)

        headers = self._create_user()
        response = self.client.post(
            "/api/v1/music/upload",
            headers=headers,
            data={"title": "My Quiet Song", "artist": "Me"},
            files={"file": ("quiet song.mp3", b"fake mp3 bytes", "audio/mpeg")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["title"], "My Quiet Song")
        self.assertTrue(body["data"]["url"].startswith("/media/music/"))
        self.assertTrue(Path(self.temp_path, Path(body["data"]["url"]).name).exists())

        db = self.SessionLocal()
        try:
            music = db.query(Music).one()
            self.assertEqual(music.title, "My Quiet Song")
            self.assertEqual(music.artist, "Me")
            self.assertIn("uploaded", music.mood_tags)
        finally:
            db.close()

    def test_music_list_requires_login_and_includes_local_files(self):
        Path(self.temp_path, "forest.mp3").write_bytes(b"fake mp3")

        response = self.client.get("/api/v1/music/list")
        self.assertEqual(response.status_code, 401)

        headers = self._create_user()
        response = self.client.get("/api/v1/music/list", headers=headers)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["music_list"][0]["title"], "forest")
        self.assertEqual(body["music_list"][0]["source"], "local")


if __name__ == "__main__":
    unittest.main()
