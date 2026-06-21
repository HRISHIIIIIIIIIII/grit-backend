from __future__ import annotations

from datetime import time

from app.models.enums import MentorTone, NotificationType
from app.models.user import UserSettings
from app.services import mentor
from app.services.mentor import EVENT_STREAK_PROTECTION
from app.services.notifications import in_quiet_hours, is_type_enabled


def test_mentor_tone_varies_copy() -> None:
    gentle = mentor.generate_mentor_message(EVENT_STREAK_PROTECTION, MentorTone.GENTLE, streak=47)
    relentless = mentor.generate_mentor_message(
        EVENT_STREAK_PROTECTION, MentorTone.RELENTLESS, streak=47
    )
    assert gentle.body != relentless.body
    assert "47" in gentle.body  # context interpolated


def test_mentor_is_deterministic() -> None:
    a = mentor.generate_mentor_message(EVENT_STREAK_PROTECTION, MentorTone.HARD, streak=10)
    b = mentor.generate_mentor_message(EVENT_STREAK_PROTECTION, MentorTone.HARD, streak=10)
    assert a == b


def test_mentor_provider_seam() -> None:
    sentinel = mentor.MentorMessage(title="LLM", body="from provider")
    mentor.set_mentor_provider(lambda event, tone, ctx: sentinel)
    try:
        msg = mentor.generate_mentor_message(EVENT_STREAK_PROTECTION, MentorTone.HARD, streak=1)
        assert msg is sentinel
    finally:
        mentor.set_mentor_provider(None)


def test_quiet_hours_overnight_window() -> None:
    settings = UserSettings(quiet_hours_start=time(22, 0), quiet_hours_end=time(7, 0))
    assert in_quiet_hours(settings, time(23, 30)) is True
    assert in_quiet_hours(settings, time(6, 0)) is True
    assert in_quiet_hours(settings, time(12, 0)) is False


def test_quiet_hours_same_day_window() -> None:
    settings = UserSettings(quiet_hours_start=time(13, 0), quiet_hours_end=time(15, 0))
    assert in_quiet_hours(settings, time(14, 0)) is True
    assert in_quiet_hours(settings, time(16, 0)) is False


def test_quiet_hours_disabled_when_unset() -> None:
    assert in_quiet_hours(UserSettings(), time(3, 0)) is False


def test_type_toggle_respected() -> None:
    settings = UserSettings(notify_streak_protection=False)
    assert is_type_enabled(settings, NotificationType.STREAK_PROTECTION) is False
    assert is_type_enabled(settings, NotificationType.MILESTONE) is True
