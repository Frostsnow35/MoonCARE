import sys
import unittest
from pathlib import Path
import re

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


class AuthFlowTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base, get_db
        from app.main import app

        # Import auth models before create_all so in-memory DB has every table.
        from app.models.auth import EmailVerificationCode  # noqa: F401
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

        import app.api.v1.auth as auth_module

        self.auth_module = auth_module
        self.original_generate_code = auth_module._generate_verification_code
        self.original_deliver_code = auth_module._deliver_email_code
        auth_module._generate_verification_code = lambda: "123456"
        auth_module._deliver_email_code = lambda email, code, purpose: None
        self.addCleanup(self._restore_auth_helpers)

    def _restore_auth_helpers(self):
        self.auth_module._generate_verification_code = self.original_generate_code
        self.auth_module._deliver_email_code = self.original_deliver_code

    def test_register_requires_verified_email_code_and_stores_secrets_safely(self):
        from app.api.v1.auth import verify_password
        from app.models.auth import EmailVerificationCode
        from app.models.user import User

        missing_code = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "USER@Example.COM",
                "password": "Strongpass123",
                "nickname": "Moon",
            },
        )
        self.assertEqual(missing_code.status_code, 422)

        send_response = self.client.post(
            "/api/v1/auth/email-code/send",
            json={"email": "USER@Example.COM", "purpose": "register"},
        )
        self.assertEqual(send_response.status_code, 200)
        self.assertNotIn("123456", send_response.text)

        wrong_code = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "USER@Example.COM",
                "password": "Strongpass123",
                "nickname": "Moon",
                "email_code": "000000",
            },
        )
        self.assertEqual(wrong_code.status_code, 400)

        register_response = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "USER@Example.COM",
                "password": "Strongpass123",
                "nickname": "Moon",
                "email_code": "123456",
            },
        )
        self.assertEqual(register_response.status_code, 200)
        body = register_response.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["email"], "user@example.com")

        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.email == "user@example.com").one()
            self.assertTrue(user.is_email_verified)
            self.assertNotEqual(user.hashed_password, "Strongpass123")
            self.assertTrue(verify_password("Strongpass123", user.hashed_password))

            code_record = db.query(EmailVerificationCode).one()
            self.assertNotEqual(code_record.code_hash, "123456")
            self.assertIsNotNone(code_record.consumed_at)
        finally:
            db.close()

    def test_forgot_password_resets_hash_and_invalidates_old_password(self):
        from app.api.v1.auth import hash_password
        from app.models.user import User

        db = self.SessionLocal()
        try:
            db.add(
                User(
                    email="reset@example.com",
                    hashed_password=hash_password("Oldpass123"),
                    nickname="Reset",
                    is_email_verified=True,
                )
            )
            db.commit()
        finally:
            db.close()

        forgot_response = self.client.post(
            "/api/v1/auth/password/forgot",
            json={"email": "RESET@example.com"},
        )
        self.assertEqual(forgot_response.status_code, 200)
        self.assertNotIn("123456", forgot_response.text)

        reset_response = self.client.post(
            "/api/v1/auth/password/reset",
            json={
                "email": "RESET@example.com",
                "email_code": "123456",
                "new_password": "Newpass123",
            },
        )
        self.assertEqual(reset_response.status_code, 200)

        old_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "reset@example.com", "password": "Oldpass123"},
        )
        self.assertEqual(old_login.status_code, 401)

        new_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "reset@example.com", "password": "Newpass123"},
        )
        self.assertEqual(new_login.status_code, 200)
        self.assertTrue(new_login.json()["access_token"])

    def test_forgot_password_does_not_reveal_unknown_accounts(self):
        from app.models.auth import EmailVerificationCode

        response = self.client.post(
            "/api/v1/auth/password/forgot",
            json={"email": "missing@example.com"},
        )
        self.assertEqual(response.status_code, 200)

        db = self.SessionLocal()
        try:
            self.assertEqual(db.query(EmailVerificationCode).count(), 0)
        finally:
            db.close()

    def test_debug_empty_login_creates_local_test_user(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "", "password": ""},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["email"], "test@mooncare.local")
        self.assertEqual(body["nickname"], "测试用户")

    def test_debug_test_account_login_creates_local_test_user(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@mooncare.local", "password": "test123456"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["email"], "test@mooncare.local")
        self.assertEqual(body["nickname"], "测试用户")


class LoginPageTests(unittest.TestCase):
    def test_login_form_does_not_require_credentials_for_dev_empty_login(self):
        login_view = (
            Path(__file__).resolve().parents[2]
            / "frontend"
            / "src"
            / "views"
            / "Login.vue"
        ).read_text(encoding="utf-8")
        email_input = re.search(r"<input\s+[^>]*v-model\.trim=\"email\"[^>]*>", login_view, re.S)
        password_input = re.search(r"<input\s+[^>]*v-model=\"password\"[^>]*>", login_view, re.S)

        self.assertIsNotNone(email_input)
        self.assertIsNotNone(password_input)
        self.assertNotIn("required", email_input.group(0))
        self.assertNotIn("required", password_input.group(0))


if __name__ == "__main__":
    unittest.main()
