"""Habits router: CRUD, check-in/undo, archive/restore."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.models.habit import Habit
from app.schemas.habit import (
    CheckinRead,
    CheckinResult,
    HabitCreate,
    HabitRead,
    HabitUpdate,
)
from app.services import habits as habit_service

router = APIRouter(prefix="/habits", tags=["Habits"])


def _to_read(habit: Habit, streak: int, checked_in_today: bool) -> HabitRead:
    read = HabitRead.model_validate(habit)
    read.current_streak = streak
    read.checked_in_today = checked_in_today
    return read


@router.get("", response_model=list[HabitRead])
async def list_habits(
    current_user: CurrentUser,
    session: DbSession,
    include_archived: bool = Query(default=False),
) -> list[HabitRead]:
    rows = await habit_service.list_habits(
        session, current_user, include_archived=include_archived
    )
    return [_to_read(h, streak, today) for h, streak, today in rows]


@router.post("", response_model=HabitRead, status_code=status.HTTP_201_CREATED)
async def create_habit(
    payload: HabitCreate, current_user: CurrentUser, session: DbSession
) -> HabitRead:
    habit = await habit_service.create_habit(session, current_user, payload)
    return _to_read(habit, 0, False)


@router.patch("/{habit_id}", response_model=HabitRead)
async def update_habit(
    habit_id: int, payload: HabitUpdate, current_user: CurrentUser, session: DbSession
) -> HabitRead:
    habit = await habit_service.update_habit(session, current_user, habit_id, payload)
    return _to_read(habit, 0, False)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: int, current_user: CurrentUser, session: DbSession
) -> None:
    await habit_service.delete_habit(session, current_user, habit_id)


@router.post("/{habit_id}/checkin", response_model=CheckinResult)
async def check_in(
    habit_id: int, current_user: CurrentUser, session: DbSession
) -> CheckinResult:
    checkin, xp, perfect, streak = await habit_service.check_in(
        session, current_user, habit_id
    )
    return CheckinResult(
        checkin=CheckinRead.model_validate(checkin),
        xp_awarded=xp,
        perfect_day=perfect,
        current_streak=streak,
    )


@router.delete("/{habit_id}/checkin", status_code=status.HTTP_204_NO_CONTENT)
async def undo_check_in(
    habit_id: int, current_user: CurrentUser, session: DbSession
) -> None:
    await habit_service.undo_check_in(session, current_user, habit_id)


@router.post("/{habit_id}/archive", response_model=HabitRead)
async def archive_habit(
    habit_id: int, current_user: CurrentUser, session: DbSession
) -> HabitRead:
    habit = await habit_service.set_archived(session, current_user, habit_id, True)
    return _to_read(habit, 0, False)


@router.post("/{habit_id}/restore", response_model=HabitRead)
async def restore_habit(
    habit_id: int, current_user: CurrentUser, session: DbSession
) -> HabitRead:
    habit = await habit_service.set_archived(session, current_user, habit_id, False)
    return _to_read(habit, 0, False)
