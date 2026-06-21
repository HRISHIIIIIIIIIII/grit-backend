from __future__ import annotations

import pytest
from app.services.gamification import (
    LEVEL_THRESHOLDS,
    MAX_LEVEL,
    level_for_xp,
    level_info,
    level_name,
)


@pytest.mark.parametrize(
    ("xp", "expected_level"),
    [
        (0, 1),
        (499, 1),
        (500, 2),
        (1_499, 2),
        (1_500, 3),
        (3_999, 3),
        (4_000, 4),
        (8_999, 4),
        (9_000, 5),
        (9_420, 5),  # Jordan Reyes
        (17_999, 5),
        (18_000, 6),
        (34_999, 6),
        (35_000, 7),
        (1_000_000, 7),
    ],
)
def test_level_for_xp(xp: int, expected_level: int) -> None:
    assert level_for_xp(xp) == expected_level


def test_level_names() -> None:
    assert level_name(1) == "Beginner"
    assert level_name(5) == "Relentless"
    assert level_name(7) == "Unstoppable"
    # Out-of-range clamps.
    assert level_name(0) == "Beginner"
    assert level_name(99) == "Unstoppable"


def test_level_info_mid_band() -> None:
    info = level_info(9_420)  # level 5 band is 9000-18000
    assert info.level == 5
    assert info.name == "Relentless"
    assert info.current_threshold == 9_000
    assert info.next_threshold == 18_000
    assert info.xp_into_level == 420
    assert info.xp_to_next == 18_000 - 9_420
    assert info.progress_pct == int(420 * 100 // 9_000)


def test_level_info_max_level() -> None:
    info = level_info(50_000)
    assert info.level == MAX_LEVEL
    assert info.next_threshold is None
    assert info.xp_to_next is None
    assert info.progress_pct == 100


def test_negative_xp_clamps_to_level_one() -> None:
    assert level_for_xp(-100) == 1
    assert level_info(-100).level == 1


def test_thresholds_match_spec() -> None:
    assert LEVEL_THRESHOLDS == (0, 500, 1_500, 4_000, 9_000, 18_000, 35_000)
