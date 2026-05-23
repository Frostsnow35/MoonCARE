from __future__ import annotations

import hmac
import logging
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from enum import Enum
from hashlib import sha256
from typing import Any

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.auth import EmailVerificationCode
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


class EmailCodePurpose(str, Enum):
    register = "register"
    reset_password = "reset_password"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    email_code: str = Field(min_length=6, max_length=6)
    nickname: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    email: str = Field(default="", max_length=128)
    password: str = Field(default="", max_length=128)


class EmailCodeRequest(BaseModel):
    email: EmailStr
    purpose: EmailCodePurpose


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    email_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    nickname: str | None


class UserResponse(BaseModel):
    id: int
    email: str
    nickname: str | None


class ApiResponse(BaseModel):
    code: int = 200
    data: dict[str, Any] = Field(default_factory=dict)
    message: str


def normalize_email(email: str) -> str:
    """Normalize email for lookup and storage."""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a password with bcrypt before storing it."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = _utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _utcnow() -> datetime:
    """Return a UTC timestamp compatible with existing naive DB columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_password_strength(password: str) -> None:
    """Reject weak account passwords before hashing."""
    if len(password) < settings.AUTH_PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"密码至少需要 {settings.AUTH_PASSWORD_MIN_LENGTH} 位",
        )
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="密码需要同时包含字母和数字",
        )


def _generate_verification_code() -> str:
    """Generate a six-digit one-time email code."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_email_code(email: str, purpose: EmailCodePurpose | str, code: str) -> str:
    """Hash a low-entropy email code with the app secret before storage."""
    purpose_value = purpose.value if isinstance(purpose, EmailCodePurpose) else purpose
    payload = f"{normalize_email(email)}:{purpose_value}:{code}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, sha256).hexdigest()


def _mask_email(email: str) -> str:
    """Mask an email address for operational logs."""
    name, _, domain = email.partition("@")
    if not domain:
        return "***"
    prefix = name[:2] if len(name) > 2 else name[:1]
    return f"{prefix}***@{domain}"


def _email_subject(purpose: EmailCodePurpose) -> str:
    if purpose == EmailCodePurpose.reset_password:
        return "MoonCARE 密码重置验证码"
    return "MoonCARE 注册邮箱验证码"


def _email_body(code: str, purpose: EmailCodePurpose) -> str:
    action = "重置密码" if purpose == EmailCodePurpose.reset_password else "完成注册"
    ttl = settings.AUTH_EMAIL_CODE_TTL_MINUTES
    return (
        f"你的 MoonCARE 验证码是：{code}\n\n"
        f"请在 {ttl} 分钟内用于{action}。如果这不是你本人操作，请忽略这封邮件。\n\n"
        "MoonCARE 仅会用此验证码确认账号操作，不会向你索要密码。"
    )


def _deliver_email_code(email: str, code: str, purpose: EmailCodePurpose) -> None:
    """Deliver an email code through SMTP, or log it in local development mode."""
    mode = settings.AUTH_EMAIL_DELIVERY_MODE.lower().strip()
    if mode == "log":
        if not settings.DEBUG:
            raise RuntimeError("AUTH_EMAIL_DELIVERY_MODE=log is only allowed when DEBUG=true")
        logger.info(
            "Local auth email code generated for %s purpose=%s code=%s",
            _mask_email(email),
            purpose.value,
            code,
        )
        return

    if mode != "smtp":
        raise RuntimeError(f"Unsupported AUTH_EMAIL_DELIVERY_MODE={settings.AUTH_EMAIL_DELIVERY_MODE}")

    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is required when AUTH_EMAIL_DELIVERY_MODE=smtp")

    message = EmailMessage()
    message["Subject"] = _email_subject(purpose)
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = email
    message.set_content(_email_body(code, purpose))

    smtp_class = smtplib.SMTP_SSL if settings.SMTP_USE_SSL else smtplib.SMTP
    with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
        if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
        server.send_message(message)


def _latest_active_code(
    db: Session,
    email: str,
    purpose: EmailCodePurpose,
    now: datetime | None = None,
) -> EmailVerificationCode | None:
    now = now or _utcnow()
    return (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == purpose.value,
            EmailVerificationCode.consumed_at.is_(None),
            EmailVerificationCode.expires_at > now,
        )
        .order_by(EmailVerificationCode.created_at.desc(), EmailVerificationCode.id.desc())
        .first()
    )


def _create_email_code(
    db: Session,
    email: str,
    purpose: EmailCodePurpose,
    user_id: int | None = None,
) -> EmailVerificationCode:
    """Create and persist a one-time code record after cooldown checks."""
    now = _utcnow()
    latest = _latest_active_code(db, email, purpose, now)
    if latest and latest.sent_at:
        elapsed = (now - latest.sent_at.replace(tzinfo=None)).total_seconds()
        if elapsed < settings.AUTH_EMAIL_CODE_RESEND_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="验证码发送过于频繁，请稍后再试",
            )

    (
        db.query(EmailVerificationCode)
        .filter(
            EmailVerificationCode.email == email,
            EmailVerificationCode.purpose == purpose.value,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .update({"consumed_at": now}, synchronize_session=False)
    )

    code = _generate_verification_code()
    record = EmailVerificationCode(
        email=email,
        purpose=purpose.value,
        code_hash=_hash_email_code(email, purpose, code),
        user_id=user_id,
        expires_at=now + timedelta(minutes=settings.AUTH_EMAIL_CODE_TTL_MINUTES),
        sent_at=now,
    )
    record._plain_code = code  # type: ignore[attr-defined]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _verify_email_code(
    db: Session,
    email: str,
    purpose: EmailCodePurpose,
    code: str,
) -> None:
    """Verify and consume a one-time email code."""
    record = _latest_active_code(db, email, purpose)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    if record.attempts >= settings.AUTH_EMAIL_CODE_MAX_ATTEMPTS:
        record.consumed_at = _utcnow()
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    expected_hash = _hash_email_code(email, purpose, code)
    if not hmac.compare_digest(record.code_hash, expected_hash):
        record.attempts += 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    record.consumed_at = _utcnow()
    db.commit()


def _token_for_user(user: User) -> TokenResponse:
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        nickname=user.nickname,
    )


def _send_code_response() -> ApiResponse:
    return ApiResponse(
        data={
            "expires_in_seconds": settings.AUTH_EMAIL_CODE_TTL_MINUTES * 60,
            "cooldown_seconds": settings.AUTH_EMAIL_CODE_RESEND_COOLDOWN_SECONDS,
        },
        message="验证码已发送，请查收邮箱",
    )


@router.post("/email-code/send", response_model=ApiResponse)
async def send_email_code(
    request: EmailCodeRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """Send a registration or password-reset email verification code."""
    email = normalize_email(request.email)
    user = db.query(User).filter(User.email == email).first()

    if request.purpose == EmailCodePurpose.register and user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已注册")

    if request.purpose == EmailCodePurpose.reset_password and not user:
        return _send_code_response()

    record = _create_email_code(db, email, request.purpose, user_id=user.id if user else None)
    plain_code = getattr(record, "_plain_code")
    try:
        _deliver_email_code(email, plain_code, request.purpose)
    except Exception as exc:
        logger.warning("Failed to deliver auth email code to %s: %s", _mask_email(email), exc)
        db.delete(record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码邮件暂时无法发送，请稍后再试",
        ) from exc

    return _send_code_response()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    """Register a user after email-code verification and password hashing."""
    email = normalize_email(user_data.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已注册")

    _validate_password_strength(user_data.password)
    _verify_email_code(db, email, EmailCodePurpose.register, user_data.email_code)

    new_user = User(
        email=email,
        hashed_password=hash_password(user_data.password),
        nickname=user_data.nickname.strip() if user_data.nickname else None,
        is_email_verified=True,
        password_changed_at=_utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info("Registered user_id=%s email=%s", new_user.id, _mask_email(email))
    return _token_for_user(new_user)


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate a user with email and password.

    开发模式特殊功能：当email和password都为空时，直接创建测试用户并登录。
    """
    email = normalize_email(user_data.email)

    # 开发模式特殊功能：当email和password都为空时，直接创建测试用户并登录
    # 默认测试用户配置：
    #   邮箱: test@mooncare.local
    #   密码: test123456
    if settings.DEBUG and not email and not user_data.password:
        logger.info("Empty login detected in DEBUG mode, creating test user")
        test_email = "test@mooncare.local"
        test_password = "test123456"
        test_user = db.query(User).filter(User.email == test_email).first()

        if not test_user:
            test_user = User(
                email=test_email,
                hashed_password=hash_password(test_password),
                nickname="测试用户",
                is_email_verified=True,
                password_changed_at=_utcnow(),
            )
            db.add(test_user)
            db.commit()
            db.refresh(test_user)
            logger.info("Created test user: %s", test_email)

        test_user.last_login_at = _utcnow()
        db.commit()
        db.refresh(test_user)
        return _token_for_user(test_user)

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    user.last_login_at = _utcnow()
    db.commit()
    db.refresh(user)
    return _token_for_user(user)


@router.post("/password/forgot", response_model=ApiResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """Start password reset without revealing whether the account exists."""
    email = normalize_email(request.email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return _send_code_response()

    record = _create_email_code(db, email, EmailCodePurpose.reset_password, user_id=user.id)
    plain_code = getattr(record, "_plain_code")
    try:
        _deliver_email_code(email, plain_code, EmailCodePurpose.reset_password)
    except Exception as exc:
        logger.warning("Failed to deliver reset email code to %s: %s", _mask_email(email), exc)
        db.delete(record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证码邮件暂时无法发送，请稍后再试",
        ) from exc

    return _send_code_response()


@router.post("/password/reset", response_model=ApiResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    """Reset a password after verifying the email code."""
    email = normalize_email(request.email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码无效或已过期")

    _validate_password_strength(request.new_password)
    _verify_email_code(db, email, EmailCodePurpose.reset_password, request.email_code)
    user.hashed_password = hash_password(request.new_password)
    user.password_changed_at = _utcnow()
    user.is_email_verified = True
    db.commit()
    logger.info("Reset password for user_id=%s email=%s", user.id, _mask_email(email))
    return ApiResponse(data={}, message="密码已重置，请重新登录")
