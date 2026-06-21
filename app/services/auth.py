"""Authentication service: registration, login, token refresh."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.streak import Streak
from app.models.user import User, UserSettings
from app.repositories import user as user_repo
from app.schemas.auth import RegisterRequest, TokenPair, UpdateMeRequest


def _validate_timezone(tz_name: str) -> None:
    try:
        ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError(f"Unknown timezone: {tz_name}") from exc


async def update_me(session: AsyncSession, user: User, payload: UpdateMeRequest) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "timezone" in data and data["timezone"] is not None:
        _validate_timezone(data["timezone"])
    # These may be explicitly cleared (set to null); others ignore null.
    nullable = {"avatar_url", "identity_word"}
    for field, value in data.items():
        if value is not None or field in nullable:
            setattr(user, field, value)
    await session.flush()
    return user


async def register(session: AsyncSession, payload: RegisterRequest) -> User:
    _validate_timezone(payload.timezone)
    existing = await user_repo.get_by_email(session, payload.email)
    if existing is not None:
        raise ConflictError("An account with this email already exists", code="email_taken")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        avatar_seed=payload.display_name[:2].upper(),
        timezone=payload.timezone,
        identity_word=payload.identity_word,
        xp_total=0,
        settings=UserSettings(),
        streak=Streak(),
    )
    await user_repo.create(session, user=user)
    return user


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    user = await user_repo.get_by_email(session, email)
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password", code="invalid_credentials")
    return user


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def refresh_tokens(session: AsyncSession, refresh_token: str) -> TokenPair:
    user_id = decode_token(refresh_token, expected_type="refresh")
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return issue_tokens(user)
