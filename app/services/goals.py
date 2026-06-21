"""Goal + milestone business logic.

Goal progress = done milestones / total. Completing a milestone awards 50 XP;
when every milestone is done the goal auto-completes. GoalHabit links a goal to
N habits.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.time import utcnow
from app.models.enums import GoalStatus, XpReason
from app.models.goal import Goal, GoalHabit, Milestone
from app.models.user import User
from app.repositories import goal as goal_repo
from app.schemas.goal import GoalCreate, GoalUpdate, MilestoneUpdate
from app.services import scoring
from app.services.gamification import XP_GOAL_MILESTONE


@dataclass
class GoalProgress:
    total: int
    done: int

    @property
    def pct(self) -> int:
        return int(self.done * 100 // self.total) if self.total else 0


def goal_progress(goal: Goal) -> GoalProgress:
    total = len(goal.milestones)
    done = sum(1 for m in goal.milestones if m.done)
    return GoalProgress(total=total, done=done)


async def _require_goal(session: AsyncSession, goal_id: int, user: User) -> Goal:
    goal = await goal_repo.get_detail(session, goal_id, user.id)
    if goal is None:
        raise NotFoundError("Goal not found")
    return goal


async def create_goal(session: AsyncSession, user: User, payload: GoalCreate) -> Goal:
    goal = Goal(
        user_id=user.id,
        name=payload.name,
        icon=payload.icon,
        color=payload.color,
        deadline=payload.deadline,
        started_at=payload.started_at,
        status=GoalStatus.ACTIVE,
    )
    session.add(goal)
    await session.flush()

    for index, m in enumerate(payload.milestones):
        session.add(
            Milestone(
                goal_id=goal.id,
                name=m.name,
                due_label=m.due_label,
                order_index=m.order_index or index,
            )
        )
    for habit_id in dict.fromkeys(payload.habit_ids):
        session.add(GoalHabit(goal_id=goal.id, habit_id=habit_id))
    await session.flush()
    return await _require_goal(session, goal.id, user)


async def update_goal(session: AsyncSession, user: User, goal_id: int, payload: GoalUpdate) -> Goal:
    goal = await _require_goal(session, goal_id, user)
    data = payload.model_dump(exclude_unset=True)
    habit_ids = data.pop("habit_ids", None)
    for field, value in data.items():
        setattr(goal, field, value)

    if habit_ids is not None:
        for link in list(goal.habit_links):
            await session.delete(link)
        await session.flush()
        for habit_id in dict.fromkeys(habit_ids):
            session.add(GoalHabit(goal_id=goal.id, habit_id=habit_id))
        await session.flush()
        # Drop the stale cached collection so the re-read reflects the new links.
        session.expire(goal, ["habit_links"])
    await session.flush()
    return await _require_goal(session, goal.id, user)


async def delete_goal(session: AsyncSession, user: User, goal_id: int) -> None:
    goal = await _require_goal(session, goal_id, user)
    await session.delete(goal)
    await session.flush()


async def list_goals(session: AsyncSession, user: User) -> list[Goal]:
    return await goal_repo.list_for_user(session, user.id)


async def get_goal(session: AsyncSession, user: User, goal_id: int) -> Goal:
    return await _require_goal(session, goal_id, user)


async def update_milestone(
    session: AsyncSession,
    user: User,
    goal_id: int,
    milestone_id: int,
    payload: MilestoneUpdate,
) -> Goal:
    await _require_goal(session, goal_id, user)  # ownership guard
    milestone = await goal_repo.get_milestone(session, goal_id, milestone_id)
    if milestone is None:
        raise NotFoundError("Milestone not found")

    data = payload.model_dump(exclude_unset=True)
    new_done = data.pop("done", None)
    for field, value in data.items():
        setattr(milestone, field, value)

    if new_done is not None and new_done != milestone.done:
        milestone.done = new_done
        if new_done:
            milestone.completed_at = utcnow()
            await scoring.award_xp(
                session,
                user,
                amount=XP_GOAL_MILESTONE,
                reason=XpReason.GOAL_MILESTONE,
                ref_id=milestone.id,
            )
        else:
            milestone.completed_at = None
            await scoring.revoke_xp_by_ref(
                session, user, reason=XpReason.GOAL_MILESTONE, ref_id=milestone.id
            )

    await session.flush()
    fresh = await _require_goal(session, goal_id, user)
    _auto_complete(fresh)
    await session.flush()
    return fresh


def _auto_complete(goal: Goal) -> None:
    progress = goal_progress(goal)
    if progress.total and progress.done == progress.total:
        if goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
    elif goal.status == GoalStatus.COMPLETED:
        # A milestone was reopened — revert to active.
        goal.status = GoalStatus.ACTIVE
