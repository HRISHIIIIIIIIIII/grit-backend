"""Password hashing (argon2) and JWT access/refresh token handling."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.time import utcnow

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def _create_token(subject: str, token_type: TokenType, expires: timedelta) -> str:
    settings = get_settings()
    now = utcnow()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | int) -> str:
    settings = get_settings()
    return _create_token(
        str(subject), "access", timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str | int) -> str:
    settings = get_settings()
    return _create_token(
        str(subject), "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str, *, expected_type: TokenType) -> int:
    """Decode and validate a JWT, returning the user id (``sub``).

    Raises :class:`UnauthorizedError` on any failure (bad signature, expiry,
    wrong token type).
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # signature, expiry, malformed
        raise UnauthorizedError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type")
    sub = payload.get("sub")
    if sub is None:
        raise UnauthorizedError("Invalid token subject")
    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject") from exc
