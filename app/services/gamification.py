"""Pure gamification math — level/XP thresholds and XP award amounts.

No database access lives here; everything is a pure function of integers so it
can be exhaustively unit-tested and reused by both the API and Celery workers.
All XP math is integer-only.
"""

from __future__ import annotations

from dataclasses import dataclass

# Level thresholds (cumulative XP required to BE at that level) and names.
# L1 starts at 0. Index 0 -> level 1.
LEVEL_THRESHOLDS: tuple[int, ...] = (0, 500, 1_500, 4_000, 9_000, 18_000, 35_000)
LEVEL_NAMES: tuple[str, ...] = (
    "Beginner",
    "Consistent",
    "Focused",
    "Disciplined",
    "Relentless",
    "Elite",
    "Unstoppable",
)
MAX_LEVEL: int = len(LEVEL_THRESHOLDS)

# XP award amounts.
XP_GOAL_MILESTONE: int = 50
XP_ROADMAP_TOPIC: int = 25
XP_PERFECT_DAY: int = 25
# Habit check-in XP is the habit's own xp_value (default 15-40); no constant here.


@dataclass(frozen=True)
class LevelInfo:
    level: int
    name: str
    current_threshold: int
    next_threshold: int | None  # None at max level
    xp_into_level: int
    xp_to_next: int | None  # None at max level
    progress_pct: int  # 0-100 within the current level band


def level_for_xp(xp_total: int) -> int:
    """Return the 1-based level for a given cumulative XP."""
    xp = max(0, xp_total)
    level = 1
    for index, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = index + 1
        else:
            break
    return level


def level_name(level: int) -> str:
    idx = min(max(level, 1), MAX_LEVEL) - 1
    return LEVEL_NAMES[idx]


def level_info(xp_total: int) -> LevelInfo:
    """Full level breakdown for progress bars."""
    xp = max(0, xp_total)
    level = level_for_xp(xp)
    current_threshold = LEVEL_THRESHOLDS[level - 1]

    if level >= MAX_LEVEL:
        return LevelInfo(
            level=level,
            name=level_name(level),
            current_threshold=current_threshold,
            next_threshold=None,
            xp_into_level=xp - current_threshold,
            xp_to_next=None,
            progress_pct=100,
        )

    next_threshold = LEVEL_THRESHOLDS[level]
    band = next_threshold - current_threshold
    xp_into_level = xp - current_threshold
    xp_to_next = next_threshold - xp
    progress_pct = int((xp_into_level * 100) // band) if band > 0 else 0
    return LevelInfo(
        level=level,
        name=level_name(level),
        current_threshold=current_threshold,
        next_threshold=next_threshold,
        xp_into_level=xp_into_level,
        xp_to_next=xp_to_next,
        progress_pct=progress_pct,
    )
