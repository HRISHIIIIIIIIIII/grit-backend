"""Import all ORM models so they register on ``Base.metadata``.

Alembic, the test DB, and the seed script import this package for its side
effects (every model class is referenced from ``__all__``).
"""

from __future__ import annotations

from app.models.achievement import Achievement, UserAchievement
from app.models.goal import Goal, GoalHabit, Milestone
from app.models.habit import Habit, HabitCheckin
from app.models.league import LeaderboardEntry, League
from app.models.notification import Notification
from app.models.roadmap import Phase, Roadmap, Topic
from app.models.streak import Streak
from app.models.user import Friendship, User, UserSettings
from app.models.xp import XpEvent

__all__ = [
    "Achievement",
    "UserAchievement",
    "Goal",
    "GoalHabit",
    "Milestone",
    "Habit",
    "HabitCheckin",
    "League",
    "LeaderboardEntry",
    "Notification",
    "Phase",
    "Roadmap",
    "Topic",
    "Streak",
    "Friendship",
    "User",
    "UserSettings",
    "XpEvent",
]
