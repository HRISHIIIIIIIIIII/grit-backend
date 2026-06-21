"""Seed the demo user "Jordan Reyes" matching the frontend sample data.

Creates: 7 habits (incl. a DSA-linked one), the 9 real learning roadmaps parsed
from ``progress_tracker/docs``, 4 goals, a 47-day streak (via back-filled
check-ins) and ~level-5 XP. Idempotent: re-running replaces the demo user.

Run with:  uv run python -m scripts.seed
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from app.core.security import hash_password
from app.core.time import local_date, utcnow
from app.db.sync_session import sync_session_scope
from app.models.enums import (
    CheckinSource,
    GoalStatus,
    HabitCategory,
    RoadmapSource,
    XpReason,
)
from app.models.goal import Goal, Milestone
from app.models.habit import Habit, HabitCheckin
from app.models.roadmap import Phase, Roadmap, Topic
from app.models.streak import Streak
from app.models.user import User, UserSettings
from app.models.xp import XpEvent
from app.services.roadmap_import import parse_roadmap_markdown
from app.services.streaks import recompute_streak
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

DEMO_EMAIL = "jordan@grit.app"
DEMO_PASSWORD = "GritDemo123!"
TARGET_XP = 9_420  # level 5 "Relentless"

DOCS_DIR = Path(__file__).resolve().parents[2] / "progress_tracker" / "docs"

# (name, category, xp_value, streak_length, is_dsa)
HABITS: list[tuple[str, HabitCategory, int, int, bool]] = [
    ("Morning run · 5km", HabitCategory.FITNESS, 30, 47, False),
    ("Cold shower", HabitCategory.DISCIPLINE, 15, 31, False),
    ("Read 20 pages", HabitCategory.LEARNING, 20, 12, False),
    ("Deep work · 90 min", HabitCategory.FOCUS, 40, 18, False),
    ("Meditate · 10 min", HabitCategory.MIND, 15, 9, False),
    ("No phone before 9", HabitCategory.DISCIPLINE, 20, 24, False),
    ("Solve a DSA topic", HabitCategory.LEARNING, 25, 14, True),
]

GOALS: list[tuple[str, str, str, list[tuple[str, bool]]]] = [
    (
        "Run a half marathon", "🏃", "#0B7A5E",
        [("5km without stopping", True), ("10km run", True), ("15km long run", True),
         ("18km long run", False), ("Race day", False)],
    ),
    (
        "Read 24 books", "📚", "#2563EB",
        [("Books 1-6", True), ("Books 7-12", True), ("Books 13-15", True),
         ("Books 16-20", False), ("Books 21-24", False)],
    ),
    (
        "Ship side project", "🚀", "#7C3AED",
        [("Design", True), ("MVP build", True), ("Beta", False), ("Launch", False),
         ("First users", False)],
    ),
    (
        "Meditate 100 days", "🧘", "#0E7490",
        [("25 days", True), ("50 days", True), ("75 days", False), ("100 days", False)],
    ),
]


def _purge_existing(session: Session) -> None:
    existing = session.execute(
        select(User).where(User.email == DEMO_EMAIL)
    ).scalar_one_or_none()
    if existing is not None:
        session.execute(delete(User).where(User.id == existing.id))
        session.flush()


def _create_user(session: Session) -> User:
    user = User(
        email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD),
        display_name="Jordan Reyes",
        avatar_seed="JR",
        timezone="Europe/Berlin",
        identity_word="Relentless",
        xp_total=0,
        settings=UserSettings(accent_color="#0EA47F"),
        streak=Streak(),
    )
    session.add(user)
    session.flush()
    return user


def _import_roadmaps(session: Session, user: User) -> Roadmap | None:
    dsa_roadmap: Roadmap | None = None
    if not DOCS_DIR.exists():
        print(f"  ! docs dir not found at {DOCS_DIR}; skipping roadmap import")
        return None

    for path in sorted(DOCS_DIR.glob("0[1-9]-*.md")):
        parsed = parse_roadmap_markdown(path.read_text(encoding="utf-8"))
        is_dsa = "dsa" in path.stem.lower()
        roadmap = Roadmap(
            user_id=user.id,
            title=parsed.title,
            source=RoadmapSource.BUILTIN,
            is_dsa_linked=is_dsa,
            icon="🧮" if is_dsa else "🗺️",
        )
        session.add(roadmap)
        session.flush()
        for p_idx, pphase in enumerate(parsed.phases):
            phase = Phase(
                roadmap_id=roadmap.id,
                name=pphase.name,
                duration_label=pphase.duration_label,
                order_index=p_idx,
            )
            session.add(phase)
            session.flush()
            for t_idx, tname in enumerate(pphase.topics):
                # Mark a slice of early topics done to show progress.
                done = is_dsa and p_idx == 0 and t_idx < 3
                session.add(
                    Topic(
                        phase_id=phase.id,
                        name=tname,
                        order_index=t_idx,
                        done=done,
                        completed_at=utcnow() if done else None,
                    )
                )
        if is_dsa:
            dsa_roadmap = roadmap
        print(f"  • imported roadmap: {parsed.title} ({len(parsed.phases)} phases)")
    session.flush()
    return dsa_roadmap


def _create_habits_and_checkins(
    session: Session, user: User, dsa_roadmap: Roadmap | None
) -> int:
    today = local_date(user.timezone)
    xp_from_checkins = 0
    active_dates: set[date] = set()

    for name, category, xp_value, streak_len, is_dsa in HABITS:
        habit = Habit(
            user_id=user.id,
            name=name,
            category=category,
            xp_value=xp_value,
            schedule="daily",
            linked_roadmap_id=dsa_roadmap.id if (is_dsa and dsa_roadmap) else None,
        )
        session.add(habit)
        session.flush()

        for i in range(streak_len):
            day = today - timedelta(days=i)
            active_dates.add(day)
            session.add(
                HabitCheckin(
                    habit_id=habit.id,
                    user_id=user.id,
                    local_date=day,
                    source=CheckinSource.ROADMAP_LINK if is_dsa else CheckinSource.MANUAL,
                )
            )
            session.add(
                XpEvent(user_id=user.id, amount=xp_value, reason=XpReason.HABIT, ref_id=habit.id)
            )
            xp_from_checkins += xp_value
    session.flush()

    # Recompute and persist the streak cache from the back-filled history.
    state = recompute_streak(active_dates, today)
    streak = session.execute(
        select(Streak).where(Streak.user_id == user.id)
    ).scalar_one()
    streak.current_daily = state.current_daily
    streak.longest = state.longest
    streak.weekly_count = state.weekly_count
    streak.monthly_count = state.monthly_count
    streak.freeze_balance = state.freeze_balance
    session.flush()
    print(f"  • streak: current={state.current_daily} longest={state.longest} "
          f"freezes={state.freeze_balance}")
    return xp_from_checkins


def _create_goals(session: Session, user: User) -> None:
    for name, icon, color, milestones in GOALS:
        all_done = all(done for _, done in milestones)
        goal = Goal(
            user_id=user.id,
            name=name,
            icon=icon,
            color=color,
            started_at=local_date(user.timezone) - timedelta(days=60),
            status=GoalStatus.COMPLETED if all_done else GoalStatus.ACTIVE,
        )
        session.add(goal)
        session.flush()
        for idx, (m_name, done) in enumerate(milestones):
            session.add(
                Milestone(
                    goal_id=goal.id,
                    name=m_name,
                    done=done,
                    completed_at=utcnow() if done else None,
                    order_index=idx,
                )
            )
    session.flush()


def _finalise_xp(session: Session, user: User, xp_from_checkins: int) -> None:
    """Top up to the target XP with a single balancing streak-bonus event."""
    balance = TARGET_XP - xp_from_checkins
    if balance > 0:
        session.add(
            XpEvent(user_id=user.id, amount=balance, reason=XpReason.STREAK_BONUS)
        )
    user.xp_total = max(TARGET_XP, xp_from_checkins)
    session.flush()


def seed() -> None:
    with sync_session_scope() as session:
        print("Seeding demo user 'Jordan Reyes'...")
        _purge_existing(session)
        user = _create_user(session)
        dsa_roadmap = _import_roadmaps(session, user)
        xp_from_checkins = _create_habits_and_checkins(session, user, dsa_roadmap)
        _create_goals(session, user)
        _finalise_xp(session, user, xp_from_checkins)
        print(f"  • xp_total={user.xp_total}")
        print(f"Done. Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
