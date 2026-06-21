"""Onboarding router: POST /onboarding (completes the wizard)."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.routers.auth import _me_response
from app.schemas.onboarding import OnboardingRequest, OnboardingResponse
from app.services import onboarding as onboarding_service

router = APIRouter(tags=["Onboarding"])


@router.post("/onboarding", response_model=OnboardingResponse)
async def complete_onboarding(
    payload: OnboardingRequest, current_user: CurrentUser, session: DbSession
) -> OnboardingResponse:
    created = await onboarding_service.complete_onboarding(session, current_user, payload)
    return OnboardingResponse(user=_me_response(current_user), habits_created=created)
