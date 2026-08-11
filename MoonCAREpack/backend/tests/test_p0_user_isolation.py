import sys
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class P0UserIsolationTests(unittest.TestCase):
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
        self.client = TestClient(app)
        self.addCleanup(lambda: app.dependency_overrides.clear())

    def _create_user(self, email: str) -> tuple[int, dict[str, str]]:
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
            return user.id, {"Authorization": f"Bearer {token}"}
        finally:
            db.close()

    def test_diary_single_record_requires_owner_for_read_update_and_delete(self):
        from app.models.mood import MoodDiary

        owner_id, _owner_headers = self._create_user("owner@example.com")
        _other_id, other_headers = self._create_user("other@example.com")

        db = self.SessionLocal()
        try:
            diary = MoodDiary(
                user_id=owner_id,
                date=datetime(2026, 5, 21, 9, 30),
                input_type="text",
                original_text="owner private diary",
                mood_level=4.0,
            )
            db.add(diary)
            db.commit()
            db.refresh(diary)
            diary_id = diary.id
        finally:
            db.close()

        read_response = self.client.get(f"/api/v1/diary/{diary_id}", headers=other_headers)
        self.assertEqual(read_response.status_code, 404)

        update_response = self.client.put(
            f"/api/v1/diary/{diary_id}",
            json={"mood_level": 9.0},
            headers=other_headers,
        )
        self.assertEqual(update_response.status_code, 404)

        delete_response = self.client.delete(f"/api/v1/diary/{diary_id}", headers=other_headers)
        self.assertEqual(delete_response.status_code, 404)

        db = self.SessionLocal()
        try:
            diary = db.query(MoodDiary).filter(MoodDiary.id == diary_id).one()
            self.assertEqual(diary.user_id, owner_id)
            self.assertEqual(diary.mood_level, 4.0)
        finally:
            db.close()

    def test_menstrual_record_requires_owner_for_update_and_delete(self):
        from app.models.menstrual import MenstrualRecord

        owner_id, _owner_headers = self._create_user("cycle-owner@example.com")
        _other_id, other_headers = self._create_user("cycle-other@example.com")

        db = self.SessionLocal()
        try:
            record = MenstrualRecord(
                user_id=owner_id,
                cycle_number=1,
                start_date=date(2026, 5, 1),
                end_date=date(2026, 5, 5),
                duration=4,
                flow_intensity=3,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            record_id = record.id
        finally:
            db.close()

        payload = {
            "start_date": "2026-05-10",
            "end_date": "2026-05-13",
            "flow_intensity": 5,
            "symptoms": ["cramps"],
            "notes": "other user overwrite attempt",
        }
        update_response = self.client.put(
            f"/api/v1/menstrual/record/{record_id}",
            json=payload,
            headers=other_headers,
        )
        self.assertEqual(update_response.status_code, 404)

        delete_response = self.client.delete(
            f"/api/v1/menstrual/record/{record_id}",
            headers=other_headers,
        )
        self.assertEqual(delete_response.status_code, 404)

        db = self.SessionLocal()
        try:
            record = db.query(MenstrualRecord).filter(MenstrualRecord.id == record_id).one()
            self.assertEqual(record.user_id, owner_id)
            self.assertEqual(record.start_date, date(2026, 5, 1))
            self.assertEqual(record.flow_intensity, 3)
        finally:
            db.close()

    def test_menstrual_create_returns_symptoms_as_list(self):
        _user_id, headers = self._create_user("cycle-create@example.com")

        response = self.client.post(
            "/api/v1/menstrual/record",
            json={
                "start_date": "2026-05-20",
                "end_date": "2026-05-22",
                "flow_intensity": 3,
                "symptoms": ["cramps", "fatigue"],
                "notes": "create response shape",
            },
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symptoms"], ["cramps", "fatigue"])

    def test_emotion_routes_ignore_query_user_id_and_use_authenticated_user(self):
        from app.models.biometric import BiometricData
        from app.models.menstrual import MenstrualRecord

        owner_id, _owner_headers = self._create_user("emotion-owner@example.com")
        _other_id, other_headers = self._create_user("emotion-other@example.com")

        db = self.SessionLocal()
        try:
            db.add(
                MenstrualRecord(
                    user_id=owner_id,
                    cycle_number=1,
                    start_date=date.today() - timedelta(days=20),
                    flow_intensity=3,
                )
            )
            db.add(
                BiometricData(
                    user_id=owner_id,
                    timestamp=datetime.now(),
                    hrv=88.0,
                    skin_temperature=36.4,
                    motion="LOW",
                    is_valid=1,
                )
            )
            db.commit()
        finally:
            db.close()

        predict_response = self.client.get(
            f"/api/v1/emotion/predict?user_id={owner_id}",
            headers=other_headers,
        )
        self.assertEqual(predict_response.status_code, 200)
        self.assertEqual(predict_response.json()["phase"], "unknown")

        intervention_response = self.client.get(
            f"/api/v1/emotion/intervention/recommend?user_id={owner_id}&context=normal",
            headers=other_headers,
        )
        self.assertEqual(intervention_response.status_code, 200)
        self.assertEqual(intervention_response.json()["recommendations"], [])

        classify_response = self.client.get(
            f"/api/v1/emotion/classify?user_id={owner_id}",
            headers=other_headers,
        )
        self.assertEqual(classify_response.status_code, 200)
        self.assertIn("error", classify_response.json())

    def test_music_recommendation_ignores_query_user_id(self):
        from app.models.biometric import BiometricData

        owner_id, _owner_headers = self._create_user("music-owner@example.com")
        other_id, other_headers = self._create_user("music-other@example.com")

        db = self.SessionLocal()
        try:
            db.add(
                BiometricData(
                    user_id=owner_id,
                    timestamp=datetime.now(),
                    hrv=20.0,
                    skin_temperature=36.8,
                    motion="LOW",
                    is_valid=1,
                )
            )
            db.add(
                BiometricData(
                    user_id=other_id,
                    timestamp=datetime.now(),
                    hrv=90.0,
                    skin_temperature=36.2,
                    motion="LOW",
                    is_valid=1,
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get(
            f"/api/v1/music/recommend?user_id={owner_id}",
            headers=other_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_emotion"], "normal")


if __name__ == "__main__":
    unittest.main()
