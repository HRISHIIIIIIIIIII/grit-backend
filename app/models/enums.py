"""Domain enumerations shared across ORM models and Pydantic schemas.

Stored as VARCHAR (``native_enum=False``) so the same models work on both
PostgreSQL and the SQLite test database without a native enum type/migration.
"""

from __future__ import annotations

import enum


class HabitCategory(str, enum.Enum):
    FITNESS = "Fitness"
    DISCIPLINE = "Discipline"
    LEARNING = "Learning"
    FOCUS = "Focus"
    MIND = "Mind"
    HEALTH = "Health"
    FINANCE = "Finance"
    CREATIVITY = "Creativity"


class CheckinSource(str, enum.Enum):
    MANUAL = "manual"
    ROADMAP_LINK = "roadmap_link"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class RoadmapSource(str, enum.Enum):
    BUILTIN = "builtin"
    IMPORTED = "imported"


class XpReason(str, enum.Enum):
    HABIT = "habit"
    GOAL_MILESTONE = "goal_milestone"
    TOPIC = "topic"
    STREAK_BONUS = "streak_bonus"
    ACHIEVEMENT = "achievement"
    PERFECT_DAY = "perfect_day"


class AchievementTier(str, enum.Enum):
    COMMON = "Common"
    RARE = "Rare"
    EPIC = "Epic"
    LEGENDARY = "Legendary"
    HIDDEN = "Hidden"


class MentorTone(str, enum.Enum):
    GENTLE = "gentle"
    HARD = "hard"
    RELENTLESS = "relentless"


class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"


class NotificationType(str, enum.Enum):
    STREAK_PROTECTION = "streak_protection"
    MILESTONE = "milestone"
    ACCOUNTABILITY = "accountability"
    REENGAGEMENT = "reengagement"
    REVIEW = "review"
    ACHIEVEMENT = "achievement"
    ENCOURAGEMENT = "encouragement"
    SOCIAL = "social"


class EvolutionStage(str, enum.Enum):
    SPARK = "Spark"
    EMBER = "Ember"
    FLAME = "Flame"
    BLAZE = "Blaze"
    INFERNO = "Inferno"
    ETERNAL = "Eternal"
