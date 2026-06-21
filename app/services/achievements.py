"""Achievement evaluation: keep the catalog, progress and unlocks in sync.

Metrics are computed from the user's data and compared against each catalog
entry's target. Newly reached targets unlock the achievement, stamp
``unlocked_at`` and award a one-time tier XP bonus.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utcnow
from app.models.achievement import Achievement, UserAchievement
from app.models.enums import GoalStatus, XpReason
from app.models.goal import Goal
from app.models.habit import Habit, HabitCheckin
from app.models.roadmap import Phase, Roadmap, Topic
from app.models.streak import Streak
from app.models.user import User
from app.models.xp import XpEvent
from app.services import scoring
from app.services.achievements_catalog import CATALOG, TIER_XP_BONUS, AchievementDef
from app.services.gamification import level_for_xp


@dataclass
class AchievementView:
    definition: AchievementDef
    progress: int
    unlocked: bool


async def _compute_metrics(session: AsyncSession, user: User) -> dict[str, int]:
    checkins = int(
        (
            await session.execute(select(func.count()).where(HabitCheckin.user_id == user.id))
        ).scalar_one()
    )
    streak = (
        await session.execute(select(Streak).where(Streak.user_id == user.id))
    ).scalar_one_or_none()
    longest = streak.longest if streak else 0
    current = streak.current_daily if streak else 0
    perfect_days = int(
        (
            await session.execute(
                select(func.count()).where(
                    XpEvent.user_id == user.id, XpEvent.reason == XpReason.PERFECT_DAY
                )
            )
        ).scalar_one()
    )
    topics_done = int(
        (
            await session.execute(
                select(func.count())
                .select_from(Topic)
                .join(Phase, Topic.phase_id == Phase.id)
                .join(Roadmap, Phase.roadmap_id == Roadmap.id)
                .where(Roadmap.user_id == user.id, Topic.done.is_(True))
            )
        ).scalar_one()
    )
    goals_completed = int(
        (
            await session.execute(
                select(func.count()).where(
                    Goal.user_id == user.id, Goal.status == GoalStatus.COMPLETED
                )
            )
        ).scalar_one()
    )
    categories = int(
        (
            await session.execute(
                select(func.count(func.distinct(Habit.category)))
                .select_from(HabitCheckin)
                .join(Habit, HabitCheckin.habit_id == Habit.id)
                .where(HabitCheckin.user_id == user.id)
            )
        ).scalar_one()
    )
    return {
        "checkins": checkins,
        "longest_streak": longest,
        "current_streak": current,
        "perfect_days": perfect_days,
        "topics_done": topics_done,
        "goals_completed": goals_completed,
        "level": level_for_xp(user.xp_total),
        "categories": categories,
    }


async def ensure_catalog(session: AsyncSession) -> dict[str, Achievement]:
    """Upsert the code-defined catalog into the Achievement table."""
    existing = {a.code: a for a in (await session.execute(select(Achievement))).scalars().all()}
    for d in CATALOG:
        row = existing.get(d.code)
        if row is None:
            row = Achievement(
                code=d.code,
                name=d.name,
                description=d.description,
                icon=d.icon,
                tier=d.tier,
                target=d.target,
                hidden=d.hidden,
            )
            session.add(row)
            existing[d.code] = row
        else:
            row.name, row.description, row.icon = d.name, d.description, d.icon
            row.tier, row.target, row.hidden = d.tier, d.target, d.hidden
    await session.flush()
    return existing


async def sync_achievements(session: AsyncSession, user: User) -> list[Achievement]:
    """Recompute progress, unlock newly earned achievements, award tier XP.

    Returns the list of achievements unlocked during this call (for notifications).
    """
    catalog_rows = await ensure_catalog(session)
    metrics = await _compute_metrics(session, user)

    links = {
        ua.achievement_id: ua
        for ua in (
            await session.execute(select(UserAchievement).where(UserAchievement.user_id == user.id))
        )
        .scalars()
        .all()
    }

    newly_unlocked: list[Achievement] = []
    for d in CATALOG:
        achievement = catalog_rows[d.code]
        value = metrics.get(d.metric, 0)
        progress = min(value, d.target)

        link = links.get(achievement.id)
        if link is None:
            link = UserAchievement(user_id=user.id, achievement_id=achievement.id)
            session.add(link)
            await session.flush()

        link.progress = progress
        if link.unlocked_at is None and value >= d.target:
            link.unlocked_at = utcnow()
            newly_unlocked.append(achievement)
            await scoring.award_xp(
                session,
                user,
                amount=TIER_XP_BONUS[d.tier],
                reason=XpReason.ACHIEVEMENT,
                ref_id=achievement.id,
            )
            await _notify_unlock(session, user, achievement)
    await session.flush()
    return newly_unlocked


async def _notify_unlock(session: AsyncSession, user: User, achievement: Achievement) -> None:
    """Dispatch an instant achievement notification (best-effort)."""
    from app.models.enums import NotificationType
    from app.services import notifications as notification_service
    from app.services.mentor import EVENT_ACHIEVEMENT

    await notification_service.notify_event(
        session,
        user,
        ntype=NotificationType.ACHIEVEMENT,
        event=EVENT_ACHIEVEMENT,
        action_label="View achievements",
        action_url="/achievements",
        achievement=achievement.name,
    )


async def list_with_progress(
    session: AsyncSession, user: User
) -> list[tuple[Achievement, UserAchievement]]:
    await sync_achievements(session, user)
    stmt = (
        select(Achievement, UserAchievement)
        .join(
            UserAchievement,
            (UserAchievement.achievement_id == Achievement.id)
            & (UserAchievement.user_id == user.id),
        )
        .order_by(Achievement.id)
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]
