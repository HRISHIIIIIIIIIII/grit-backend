"""Auth router: register, login, refresh, logout, and /me."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserPublic,
)
from app.services import auth as auth_service
from app.services.gamification import level_info

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession) -> UserPublic:
    user = await auth_service.register(session, payload)
    await session.flush()
    return UserPublic.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: DbSession) -> TokenPair:
    user = await auth_service.authenticate(session, payload.email, payload.password)
    return auth_service.issue_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenPair:
    return await auth_service.refresh_tokens(session, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(_: CurrentUser) -> None:
    # Stateless JWT: logout is a client-side token discard. Endpoint exists so the
    # frontend has a consistent action and we can hang token revocation here later.
    return None


# GET /me lives at the API root per the spec, so it gets its own prefix-less router.
me_router = APIRouter(tags=["Auth"])


@me_router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser) -> MeResponse:
    info = level_info(current_user.xp_total)
    base = UserPublic.model_validate(current_user).model_dump()
    return MeResponse(**base, level=info.level, level_name=info.name, xp_to_next=info.xp_to_next)
