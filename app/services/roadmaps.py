"""Roadmap business logic: import, listing with progress, topic toggling.

Toggling a topic done on an ``is_dsa_linked`` roadmap credits the user's linked
DSA habit for today (idempotently) and awards roadmap-topic XP.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.time import local_date, utcnow
from app.models.enums import CheckinSource, RoadmapSource, XpReason
from app.models.roadmap import Phase, Roadmap, Topic
from app.models.user import User
from app.repositories import habit as habit_repo
from app.repositories import roadmap as roadmap_repo
from app.services import habits as habit_service
from app.services import scoring
from app.services.gamification import XP_ROADMAP_TOPIC
from app.services.roadmap_import import parse_roadmap_markdown


@dataclass
class RoadmapProgress:
    total: int
    done: int

    @property
    def pct(self) -> int:
        return int(self.done * 100 // self.total) if self.total else 0


def topic_progress(topics: list[Topic]) -> RoadmapProgress:
    return RoadmapProgress(total=len(topics), done=sum(1 for t in topics if t.done))


def roadmap_progress(roadmap: Roadmap) -> RoadmapProgress:
    total = 0
    done = 0
    for phase in roadmap.phases:
        for topic in phase.topics:
            total += 1
            done += 1 if topic.done else 0
    return RoadmapProgress(total=total, done=done)


async def import_roadmap(
    session: AsyncSession,
    user: User,
    *,
    markdown: str,
    icon: str | None = None,
    color: str | None = None,
    is_dsa_linked: bool = False,
) -> Roadmap:
    parsed = parse_roadmap_markdown(markdown)
    roadmap = Roadmap(
        user_id=user.id,
        title=parsed.title,
        icon=icon,
        color=color,
        source=RoadmapSource.IMPORTED,
        is_dsa_linked=is_dsa_linked,
    )
    session.add(roadmap)
    await session.flush()

    for p_index, parsed_phase in enumerate(parsed.phases):
        phase = Phase(
            roadmap_id=roadmap.id,
            name=parsed_phase.name,
            duration_label=parsed_phase.duration_label,
            order_index=p_index,
        )
        session.add(phase)
        await session.flush()
        for t_index, topic_name in enumerate(parsed_phase.topics):
            session.add(Topic(phase_id=phase.id, name=topic_name, order_index=t_index))
    await session.flush()
    return roadmap


async def list_roadmaps(session: AsyncSession, user: User) -> list[Roadmap]:
    return await roadmap_repo.list_for_user(session, user.id)


async def get_roadmap(session: AsyncSession, user: User, roadmap_id: int) -> Roadmap:
    roadmap = await roadmap_repo.get_detail(session, roadmap_id, user.id)
    if roadmap is None:
        raise NotFoundError("Roadmap not found")
    return roadmap


@dataclass
class ToggleOutcome:
    topic: Topic
    phase_complete: bool
    roadmap_pct: int
    xp_awarded: int
    dsa_credited: bool


async def toggle_topic(
    session: AsyncSession, user: User, topic_id: int, done: bool
) -> ToggleOutcome:
    found = await roadmap_repo.get_topic_owned(session, topic_id, user.id)
    if found is None:
        raise NotFoundError("Topic not found")
    topic, phase, roadmap = found

    xp_awarded = 0
    dsa_credited = False

    if done != topic.done:
        topic.done = done
        topic.completed_at = utcnow() if done else None
        await session.flush()

        if done:
            await scoring.award_xp(
                session, user, amount=XP_ROADMAP_TOPIC, reason=XpReason.TOPIC, ref_id=topic.id
            )
            xp_awarded = XP_ROADMAP_TOPIC
            if roadmap.is_dsa_linked:
                dsa_credited = await _credit_dsa_habit(session, user, roadmap.id)
        else:
            await scoring.revoke_xp_by_ref(session, user, reason=XpReason.TOPIC, ref_id=topic.id)

    phase_topics = await roadmap_repo.phase_topics(session, phase.id)
    phase_complete = bool(phase_topics) and all(t.done for t in phase_topics)

    all_topics = await roadmap_repo.all_topics(session, roadmap.id)
    progress = topic_progress(all_topics)

    return ToggleOutcome(
        topic=topic,
        phase_complete=phase_complete,
        roadmap_pct=progress.pct,
        xp_awarded=xp_awarded,
        dsa_credited=dsa_credited,
    )


async def _credit_dsa_habit(session: AsyncSession, user: User, roadmap_id: int) -> bool:
    """Check in the DSA habit linked to this roadmap for today, if not already done."""
    habit = await roadmap_repo.linked_dsa_habit(session, user.id, roadmap_id)
    if habit is None:
        return False
    today = local_date(user.timezone)
    if await habit_repo.checkin_for_day(session, habit.id, today) is not None:
        return False
    await habit_service.check_in(session, user, habit.id, source=CheckinSource.ROADMAP_LINK)
    return True
