"""Aggregates all versioned routers under ``/api/v1``.

Each domain router is included here as it is implemented.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.routers import (
    achievements,
    auth,
    community,
    goals,
    habits,
    notifications,
    progress,
    roadmaps,
    settings,
    streaks,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(auth.me_router)
api_router.include_router(habits.router)
api_router.include_router(streaks.router)
api_router.include_router(progress.router)
api_router.include_router(roadmaps.router)
api_router.include_router(goals.router)
api_router.include_router(achievements.router)
api_router.include_router(community.router)
api_router.include_router(notifications.router)
api_router.include_router(settings.router)
