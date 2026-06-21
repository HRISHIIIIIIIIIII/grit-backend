"""Community business logic: leaderboards, friendships, weekly challenges.

Friends and Global boards rank by all-time ``xp_total``; the League board ranks
by XP earned in the current local ISO week. Challenges are computed weekly
targets (no persistence) so the frontend always has fresh goals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.time import local_date, start_of_local_day_utc
from app.models.enums import FriendshipStatus
from app.models.user import Friendship, User
from app.repositories import community as community_repo
from app.repositories import progress as progress_repo
from app.repositories import user as user_repo
from app.schemas.community import (
    ChallengeRead,
    FriendRead,
    LeaderboardEntryRead,
)
from app.services.gamification import level_for_xp


def _week_start_utc(user: User) -> datetime:
    today = local_date(user.timezone)
    monday = today - timedelta(days=today.weekday())
    return start_of_local_day_utc(user.timezone, monday)


@dataclass
class Board:
    entries: list[LeaderboardEntryRead]
    my_rank: int | None


def _rank(users_xp: list[tuple[User, int]], me_id: int) -> Board:
    ordered = sorted(users_xp, key=lambda t: (-t[1], t[0].id))
    entries: list[LeaderboardEntryRead] = []
    my_rank: int | None = None
    for index, (user, xp) in enumerate(ordered, start=1):
        is_me = user.id == me_id
        if is_me:
            my_rank = index
        entries.append(
            LeaderboardEntryRead(
                rank=index,
                user_id=user.id,
                display_name=user.display_name,
                avatar_seed=user.avatar_seed,
                level=level_for_xp(user.xp_total),
                xp=xp,
                is_me=is_me,
            )
        )
    return Board(entries=entries, my_rank=my_rank)


async def leaderboard(session: AsyncSession, user: User, scope: str) -> Board:
    if scope == "friends":
        ids = await community_repo.accepted_friend_ids(session, user.id)
        ids.append(user.id)
        friend_map = await community_repo.users_by_ids(session, ids)
        return _rank([(u, u.xp_total) for u in friend_map.values()], user.id)

    if scope == "league":
        members = await community_repo.public_users_by_xp(session, limit=30)
        if user.id not in {u.id for u in members}:
            members.append(user)
        since = _week_start_utc(user)
        weekly = await community_repo.weekly_xp_for_users(
            session, [u.id for u in members], since
        )
        return _rank([(u, weekly.get(u.id, 0)) for u in members], user.id)

    # global (default) — all-time xp_total.
    public = await community_repo.public_users_by_xp(session, limit=100)
    if user.id not in {u.id for u in public}:
        public.append(user)
    return _rank([(u, u.xp_total) for u in public], user.id)


# --- Friends -------------------------------------------------------------


def _friend_read(other: User, friendship: Friendship, direction: str) -> FriendRead:
    return FriendRead(
        friendship_id=friendship.id,
        user_id=other.id,
        display_name=other.display_name,
        avatar_seed=other.avatar_seed,
        level=level_for_xp(other.xp_total),
        xp_total=other.xp_total,
        status=friendship.status.value,
        direction=direction,
    )


async def list_friends(
    session: AsyncSession, user: User
) -> tuple[list[FriendRead], list[FriendRead], list[FriendRead]]:
    friendships = await community_repo.friendships_for(session, user.id)
    other_ids = [
        f.friend_id if f.user_id == user.id else f.user_id for f in friendships
    ]
    others = await community_repo.users_by_ids(session, other_ids)

    friends: list[FriendRead] = []
    incoming: list[FriendRead] = []
    outgoing: list[FriendRead] = []
    for f in friendships:
        other_id = f.friend_id if f.user_id == user.id else f.user_id
        other = others.get(other_id)
        if other is None:
            continue
        if f.status == FriendshipStatus.ACCEPTED:
            friends.append(_friend_read(other, f, "mutual"))
        elif f.status == FriendshipStatus.PENDING:
            if f.friend_id == user.id:
                incoming.append(_friend_read(other, f, "incoming"))
            else:
                outgoing.append(_friend_read(other, f, "outgoing"))
    return friends, incoming, outgoing


async def send_request(session: AsyncSession, user: User, email: str) -> Friendship:
    target = await user_repo.get_by_email(session, email)
    if target is None:
        raise NotFoundError("No user with that email", code="user_not_found")
    if target.id == user.id:
        raise ValidationError("You cannot add yourself", code="self_friend")
    if await community_repo.existing_friendship(session, user.id, target.id):
        raise ConflictError("A friendship or request already exists", code="already_friends")

    friendship = Friendship(
        user_id=user.id, friend_id=target.id, status=FriendshipStatus.PENDING
    )
    session.add(friendship)
    await session.flush()
    return friendship


async def respond_request(
    session: AsyncSession, user: User, friendship_id: int, accept: bool
) -> Friendship | None:
    friendship = await session.get(Friendship, friendship_id)
    if (
        friendship is None
        or friendship.friend_id != user.id
        or friendship.status != FriendshipStatus.PENDING
    ):
        raise NotFoundError("Friend request not found", code="request_not_found")

    if accept:
        friendship.status = FriendshipStatus.ACCEPTED
        await session.flush()
        return friendship
    await session.delete(friendship)
    await session.flush()
    return None


# --- Challenges (computed weekly) ----------------------------------------


async def weekly_challenges(session: AsyncSession, user: User) -> list[ChallengeRead]:
    today = local_date(user.timezone)
    start = today - timedelta(days=today.weekday())
    checkins = await progress_repo.total_checkins(session, user.id, start, today)
    perfect = await progress_repo.perfect_day_count(session, user.id, start, today)

    defs = [
        ("consistency_20", "Consistency", "Log 20 check-ins this week.", 20, checkins),
        ("perfect_3", "Perfect Trio", "Have 3 perfect days this week.", 3, perfect),
        ("perfect_week", "Perfect Week", "Have 7 perfect days this week.", 7, perfect),
    ]
    return [
        ChallengeRead(
            code=code,
            name=name,
            description=desc,
            target=target,
            progress=min(value, target),
            complete=value >= target,
        )
        for code, name, desc, target, value in defs
    ]
