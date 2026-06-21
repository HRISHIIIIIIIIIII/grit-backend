"""Static achievement catalog (source of truth).

Each entry maps to a single integer *metric* computed from the user's data; the
achievement unlocks when that metric reaches ``target``. Hidden achievements keep
their name/criteria masked until unlocked.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import AchievementTier


@dataclass(frozen=True)
class AchievementDef:
    code: str
    name: str
    description: str
    icon: str
    tier: AchievementTier
    metric: str
    target: int
    hidden: bool = False


# XP bonus granted once when an achievement unlocks, by tier.
TIER_XP_BONUS: dict[AchievementTier, int] = {
    AchievementTier.COMMON: 50,
    AchievementTier.RARE: 100,
    AchievementTier.EPIC: 200,
    AchievementTier.LEGENDARY: 500,
    AchievementTier.HIDDEN: 150,
}


CATALOG: tuple[AchievementDef, ...] = (
    AchievementDef(
        "first_step",
        "First Step",
        "Complete your first habit check-in.",
        "👣",
        AchievementTier.COMMON,
        "checkins",
        1,
    ),
    AchievementDef(
        "getting_consistent",
        "Getting Consistent",
        "Reach a 7-day streak.",
        "🌱",
        AchievementTier.COMMON,
        "longest_streak",
        7,
    ),
    AchievementDef(
        "on_fire",
        "On Fire",
        "Reach a 21-day streak.",
        "🔥",
        AchievementTier.RARE,
        "longest_streak",
        21,
    ),
    AchievementDef(
        "blaze_runner",
        "Blaze Runner",
        "Reach a 46-day streak.",
        "🚀",
        AchievementTier.EPIC,
        "longest_streak",
        46,
    ),
    AchievementDef(
        "centurion",
        "Centurion",
        "Reach a 100-day streak.",
        "💯",
        AchievementTier.LEGENDARY,
        "longest_streak",
        100,
    ),
    AchievementDef(
        "perfectionist",
        "Perfectionist",
        "Log 10 perfect days.",
        "✨",
        AchievementTier.RARE,
        "perfect_days",
        10,
    ),
    AchievementDef(
        "grinder",
        "Grinder",
        "Complete 100 habit check-ins.",
        "⚙️",
        AchievementTier.EPIC,
        "checkins",
        100,
    ),
    AchievementDef(
        "scholar",
        "Scholar",
        "Finish 25 roadmap topics.",
        "📚",
        AchievementTier.RARE,
        "topics_done",
        25,
    ),
    AchievementDef(
        "goal_getter",
        "Goal Getter",
        "Complete your first goal.",
        "🎯",
        AchievementTier.RARE,
        "goals_completed",
        1,
    ),
    AchievementDef(
        "relentless",
        "Relentless",
        "Reach level 5.",
        "🏆",
        AchievementTier.EPIC,
        "level",
        5,
    ),
    AchievementDef(
        "polymath",
        "Polymath",
        "Check in habits across 6 different categories.",
        "🧠",
        AchievementTier.HIDDEN,
        "categories",
        6,
        hidden=True,
    ),
)


def by_code() -> dict[str, AchievementDef]:
    return {a.code: a for a in CATALOG}
