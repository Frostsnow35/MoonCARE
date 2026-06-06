import re
import sys
import unittest
from pathlib import Path

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
        self.original_debug = auth_module.settings.DEBUG
        auth_module._generate_verification_code = lambda: "123456"
        auth_module._deliver_email_code = lambda email, code, purpose: None
        auth_module.settings.DEBUG = True
        self.addCleanup(self._restore_auth_helpers)

    def _restore_auth_helpers(self):
        self.auth_module._generate_verification_code = self.original_generate_code
        self.auth_module._deliver_email_code = self.original_deliver_code
        self.auth_module.settings.DEBUG = self.original_debug

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

    def test_send_email_code_succeeds_in_log_mode_without_debug(self):
        from app.models.auth import EmailVerificationCode

        original_debug = self.auth_module.settings.DEBUG
        original_mode = self.auth_module.settings.AUTH_EMAIL_DELIVERY_MODE
        self.addCleanup(setattr, self.auth_module.settings, "DEBUG", original_debug)
        self.addCleanup(
            setattr,
            self.auth_module.settings,
            "AUTH_EMAIL_DELIVERY_MODE",
            original_mode,
        )
        self.auth_module.settings.DEBUG = False
        self.auth_module.settings.AUTH_EMAIL_DELIVERY_MODE = "log"
        self.auth_module._deliver_email_code = self.original_deliver_code

        response = self.client.post(
            "/api/v1/auth/email-code/send",
            json={"email": "local-log@example.com", "purpose": "register"},
        )

        self.assertEqual(response.status_code, 200)
        db = self.SessionLocal()
        try:
            self.assertEqual(db.query(EmailVerificationCode).count(), 1)
        finally:
            db.close()

    def test_send_email_code_in_debug_log_mode_returns_debug_code(self):
        original_debug = self.auth_module.settings.DEBUG
        original_mode = self.auth_module.settings.AUTH_EMAIL_DELIVERY_MODE
        self.addCleanup(setattr, self.auth_module.settings, "DEBUG", original_debug)
        self.addCleanup(
            setattr,
            self.auth_module.settings,
            "AUTH_EMAIL_DELIVERY_MODE",
            original_mode,
        )
        self.auth_module.settings.DEBUG = True
        self.auth_module.settings.AUTH_EMAIL_DELIVERY_MODE = "log"

        response = self.client.post(
            "/api/v1/auth/email-code/send",
            json={"email": "debug-register@example.com", "purpose": "register"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"].get("debug_email_code"), "123456")

    def test_forgot_password_in_debug_log_mode_returns_debug_code(self):
        from app.api.v1.auth import hash_password
        from app.models.user import User

        db = self.SessionLocal()
        try:
            db.add(
                User(
                    email="debug-reset@example.com",
                    hashed_password=hash_password("Oldpass123"),
                    nickname="DebugReset",
                    is_email_verified=True,
                )
            )
            db.commit()
        finally:
            db.close()

        original_debug = self.auth_module.settings.DEBUG
        original_mode = self.auth_module.settings.AUTH_EMAIL_DELIVERY_MODE
        self.addCleanup(setattr, self.auth_module.settings, "DEBUG", original_debug)
        self.addCleanup(
            setattr,
            self.auth_module.settings,
            "AUTH_EMAIL_DELIVERY_MODE",
            original_mode,
        )
        self.auth_module.settings.DEBUG = True
        self.auth_module.settings.AUTH_EMAIL_DELIVERY_MODE = "log"

        response = self.client.post(
            "/api/v1/auth/password/forgot",
            json={"email": "debug-reset@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"].get("debug_email_code"), "123456")

    def test_register_requires_unique_nickname(self):
        from app.models.user import User

        missing_nickname = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "missing-nickname@example.com",
                "password": "Strongpass123",
                "email_code": "123456",
            },
        )
        self.assertEqual(missing_nickname.status_code, 422)

        blank_nickname = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "blank-nickname@example.com",
                "password": "Strongpass123",
                "nickname": "   ",
                "email_code": "123456",
            },
        )
        self.assertEqual(blank_nickname.status_code, 422)

        first_send = self.client.post(
            "/api/v1/auth/email-code/send",
            json={"email": "first@example.com", "purpose": "register"},
        )
        self.assertEqual(first_send.status_code, 200)

        first_register = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "first@example.com",
                "password": "Strongpass123",
                "nickname": "adminMC",
                "email_code": "123456",
            },
        )
        self.assertEqual(first_register.status_code, 200)

        second_send = self.client.post(
            "/api/v1/auth/email-code/send",
            json={"email": "second@example.com", "purpose": "register"},
        )
        self.assertEqual(second_send.status_code, 200)

        duplicate_nickname = self.client.post(
            "/api/v1/auth/register",
            json={
                "email": "second@example.com",
                "password": "Strongpass123",
                "nickname": "adminMC",
                "email_code": "123456",
            },
        )
        self.assertEqual(duplicate_nickname.status_code, 400)

        db = self.SessionLocal()
        try:
            self.assertEqual(db.query(User).count(), 1)
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
        self.assertTrue(body["nickname"])

    def test_debug_test_account_login_creates_local_test_user(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "test@mooncare.local", "password": "test123456"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["access_token"])
        self.assertEqual(body["email"], "test@mooncare.local")
        self.assertTrue(body["nickname"])

    def test_login_accepts_nickname_identifier(self):
        from app.api.v1.auth import hash_password
        from app.models.user import User

        db = self.SessionLocal()
        try:
            db.add(
                User(
                    email="admin@example.com",
                    hashed_password=hash_password("Strongpass123"),
                    nickname="adminMC",
                    is_email_verified=True,
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "adminMC", "password": "Strongpass123"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nickname"], "adminMC")


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

    def test_login_view_mentions_nickname_identifier(self):
        login_view = (
            Path(__file__).resolve().parents[2]
            / "frontend"
            / "src"
            / "views"
            / "Login.vue"
        ).read_text(encoding="utf-8")

        self.assertIn("邮箱或昵称", login_view)


class RegisterPageTests(unittest.TestCase):
    def test_register_view_requires_nickname(self):
        register_view = (
            Path(__file__).resolve().parents[2]
            / "frontend"
            / "src"
            / "views"
            / "Register.vue"
        ).read_text(encoding="utf-8")
        nickname_input = re.search(r"<input\s+[^>]*v-model\.trim=\"nickname\"[^>]*>", register_view, re.S)

        self.assertIsNotNone(nickname_input)
        self.assertIn("required", nickname_input.group(0))
        self.assertNotIn("可选", register_view)


if __name__ == "__main__":
    unittest.main()
