"""Shared FastAPI dependencies: DB session and the authenticated user."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories import user as user_repo

_bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication required")
    user_id = decode_token(credentials.credentials, expected_type="access")
    user = await user_repo.get_by_id(session, user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
