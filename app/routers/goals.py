"""Goals router: CRUD + milestone updates."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.models.goal import Goal
from app.schemas.goal import (
    GoalCreate,
    GoalRead,
    GoalUpdate,
    MilestoneRead,
    MilestoneUpdate,
)
from app.services import goals as goal_service

router = APIRouter(prefix="/goals", tags=["Goals"])


def _to_read(goal: Goal) -> GoalRead:
    progress = goal_service.goal_progress(goal)
    read = GoalRead.model_validate(goal)
    read.milestones = sorted(
        (MilestoneRead.model_validate(m) for m in goal.milestones),
        key=lambda m: (m.order_index, m.id),
    )
    read.habit_ids = [link.habit_id for link in goal.habit_links]
    read.done_milestones = progress.done
    read.total_milestones = progress.total
    read.progress_pct = progress.pct
    return read


@router.get("", response_model=list[GoalRead])
async def list_goals(current_user: CurrentUser, session: DbSession) -> list[GoalRead]:
    goals = await goal_service.list_goals(session, current_user)
    return [_to_read(g) for g in goals]


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate, current_user: CurrentUser, session: DbSession
) -> GoalRead:
    goal = await goal_service.create_goal(session, current_user, payload)
    return _to_read(goal)


@router.get("/{goal_id}", response_model=GoalRead)
async def get_goal(goal_id: int, current_user: CurrentUser, session: DbSession) -> GoalRead:
    goal = await goal_service.get_goal(session, current_user, goal_id)
    return _to_read(goal)


@router.patch("/{goal_id}", response_model=GoalRead)
async def update_goal(
    goal_id: int, payload: GoalUpdate, current_user: CurrentUser, session: DbSession
) -> GoalRead:
    goal = await goal_service.update_goal(session, current_user, goal_id, payload)
    return _to_read(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: int, current_user: CurrentUser, session: DbSession) -> None:
    await goal_service.delete_goal(session, current_user, goal_id)


@router.patch("/{goal_id}/milestones/{milestone_id}", response_model=GoalRead)
async def update_milestone(
    goal_id: int,
    milestone_id: int,
    payload: MilestoneUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> GoalRead:
    goal = await goal_service.update_milestone(
        session, current_user, goal_id, milestone_id, payload
    )
    return _to_read(goal)
