# ruff: noqa: E501  — mentor copy strings are intentionally kept on one line for readability.
"""ATLAS — the in-app mentor copy engine.

``generate_mentor_message(event, tone, **context)`` returns a title/body pair
drawn from a curated, ORIGINAL message library keyed by (event, tone). No
third-party quotes are used.

An adapter seam lets an LLM provider be swapped in later: register a callable via
``set_mentor_provider``; if it returns a message that is used, otherwise we fall
back to the static library. The library is deterministic (variant chosen from the
context) so tests and re-renders are stable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.models.enums import MentorTone

# Canonical mentor event keys (a superset of notification types ATLAS speaks to).
EVENT_STREAK_PROTECTION = "streak_protection"
EVENT_ACCOUNTABILITY = "accountability"
EVENT_REENGAGEMENT = "reengagement"
EVENT_REVIEW_WEEKLY = "review_weekly"
EVENT_REVIEW_MONTHLY = "review_monthly"
EVENT_MILESTONE = "milestone"
EVENT_ACHIEVEMENT = "achievement"
EVENT_ENCOURAGEMENT = "encouragement"


@dataclass(frozen=True)
class MentorMessage:
    title: str
    body: str


@dataclass(frozen=True)
class _Variant:
    title: str
    body: str


# (event, tone) -> ordered list of template variants. Bodies may reference
# context keys via str.format (e.g. {streak}, {habit}, {name}).
_LIBRARY: dict[tuple[str, MentorTone], list[_Variant]] = {
    (EVENT_STREAK_PROTECTION, MentorTone.GENTLE): [
        _Variant(
            "Your streak is waiting",
            "A {streak}-day streak is still alive. A few minutes now keeps it glowing.",
        ),
        _Variant(
            "One small step",
            "You've come {streak} days. Tonight's check-in is all it takes to carry it forward.",
        ),
    ],
    (EVENT_STREAK_PROTECTION, MentorTone.HARD): [
        _Variant(
            "Don't drop it now",
            "{streak} days of work is on the line tonight. Close the loop before midnight.",
        ),
        _Variant(
            "Protect the streak",
            "You didn't build {streak} days to lose them to one lazy evening. Check in.",
        ),
    ],
    (EVENT_STREAK_PROTECTION, MentorTone.RELENTLESS): [
        _Variant("No excuses", "{streak} days. Zero reasons to break it. Move."),
        _Variant(
            "Finish the day",
            "The streak doesn't care that you're tired. {streak} days say show up. Now.",
        ),
    ],
    (EVENT_ACCOUNTABILITY, MentorTone.GENTLE): [
        _Variant(
            "Yesterday slipped",
            "No guilt — yesterday is gone. Today is open. Start with one habit.",
        ),
    ],
    (EVENT_ACCOUNTABILITY, MentorTone.HARD): [
        _Variant("You missed a day", "Yesterday is a miss. Today is a choice. Make it count."),
    ],
    (EVENT_ACCOUNTABILITY, MentorTone.RELENTLESS): [
        _Variant("Back on the bar", "You broke rhythm. Rebuild it today — no negotiation."),
    ],
    (EVENT_REENGAGEMENT, MentorTone.GENTLE): [
        _Variant(
            "We saved your spot",
            "It's been a little while. Your habits are right where you left them whenever you're ready.",
        ),
    ],
    (EVENT_REENGAGEMENT, MentorTone.HARD): [
        _Variant(
            "Time to return",
            "A few days off becomes a few weeks fast. Come back and reset the clock today.",
        ),
    ],
    (EVENT_REENGAGEMENT, MentorTone.RELENTLESS): [
        _Variant(
            "Stop drifting",
            "Momentum is rotting while you wait. One check-in restarts the engine. Do it.",
        ),
    ],
    (EVENT_REVIEW_WEEKLY, MentorTone.GENTLE): [
        _Variant(
            "Your week in review",
            "You logged {checkins} check-ins this week. Quiet, steady progress counts.",
        ),
    ],
    (EVENT_REVIEW_WEEKLY, MentorTone.HARD): [
        _Variant(
            "Weekly scoreboard",
            "{checkins} check-ins this week. Look at the number, then beat it next week.",
        ),
    ],
    (EVENT_REVIEW_WEEKLY, MentorTone.RELENTLESS): [
        _Variant(
            "Week closed",
            "{checkins} check-ins. Good. Now raise the floor — next week starts harder.",
        ),
    ],
    (EVENT_REVIEW_MONTHLY, MentorTone.GENTLE): [
        _Variant(
            "A month of you",
            "This month you showed up {checkins} times. That's who you're becoming.",
        ),
    ],
    (EVENT_REVIEW_MONTHLY, MentorTone.HARD): [
        _Variant(
            "Monthly tally", "{checkins} check-ins this month. Discipline is a number now. Grow it."
        ),
    ],
    (EVENT_REVIEW_MONTHLY, MentorTone.RELENTLESS): [
        _Variant(
            "Month logged", "{checkins} this month. The identity is forming. Don't soften now."
        ),
    ],
    (EVENT_MILESTONE, MentorTone.GENTLE): [
        _Variant("Milestone reached", 'You completed "{milestone}". Lovely work — onto the next.'),
    ],
    (EVENT_MILESTONE, MentorTone.HARD): [
        _Variant("Milestone down", '"{milestone}" is done. Bank it and line up the next target.'),
    ],
    (EVENT_MILESTONE, MentorTone.RELENTLESS): [
        _Variant("One down", '"{milestone}" cleared. Don\'t celebrate long — keep climbing.'),
    ],
    (EVENT_ACHIEVEMENT, MentorTone.GENTLE): [
        _Variant(
            "Achievement unlocked", 'You earned "{achievement}". A real sign of your consistency.'
        ),
    ],
    (EVENT_ACHIEVEMENT, MentorTone.HARD): [
        _Variant(
            "Unlocked: {achievement}",
            'Earned, not given. "{achievement}" is yours. Go get the next one.',
        ),
    ],
    (EVENT_ACHIEVEMENT, MentorTone.RELENTLESS): [
        _Variant(
            "Trophy taken",
            '"{achievement}" unlocked. Proof you can do hard things. Again tomorrow.',
        ),
    ],
    (EVENT_ENCOURAGEMENT, MentorTone.GENTLE): [
        _Variant("You're doing well", "Steady as you go, {name}. Small reps, big identity."),
    ],
    (EVENT_ENCOURAGEMENT, MentorTone.HARD): [
        _Variant("Keep pushing", "Comfort is the enemy, {name}. Stack another rep today."),
    ],
    (EVENT_ENCOURAGEMENT, MentorTone.RELENTLESS): [
        _Variant("Go again", "No coasting, {name}. The standard is every single day."),
    ],
}


MentorProvider = Callable[[str, MentorTone, dict[str, object]], MentorMessage | None]
_provider: MentorProvider | None = None


def set_mentor_provider(provider: MentorProvider | None) -> None:
    """Register (or clear) an LLM-backed provider. Used by future integrations."""
    global _provider
    _provider = provider


def _safe_format(text: str, context: dict[str, object]) -> str:
    try:
        return text.format(**context)
    except (KeyError, IndexError):
        return text


def _from_library(event: str, tone: MentorTone, context: dict[str, object]) -> MentorMessage:
    variants = _LIBRARY.get((event, tone))
    if not variants:
        # Fall back to the relentless/hard default, then a generic line.
        variants = _LIBRARY.get((event, MentorTone.HARD)) or [
            _Variant("Keep going", "Show up today. That's the whole secret.")
        ]
    # Deterministic variant selection from a numeric context hint.
    raw = context.get("variant", context.get("streak", 0))
    seed = raw if isinstance(raw, int) else 0
    variant = variants[seed % len(variants)]
    return MentorMessage(
        title=_safe_format(variant.title, context),
        body=_safe_format(variant.body, context),
    )


def generate_mentor_message(event: str, tone: MentorTone, **context: object) -> MentorMessage:
    if _provider is not None:
        produced = _provider(event, tone, context)
        if produced is not None:
            return produced
    return _from_library(event, tone, context)
