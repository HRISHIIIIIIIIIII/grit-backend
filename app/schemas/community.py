"""Community schemas: leaderboard, friends, challenges."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class LeaderboardEntryRead(BaseModel):
    rank: int
    user_id: int
    display_name: str
    avatar_seed: str | None
    level: int
    xp: int  # all-time xp_total or weekly xp depending on scope
    is_me: bool


class LeaderboardRead(BaseModel):
    scope: str
    entries: list[LeaderboardEntryRead]
    my_rank: int | None


class FriendRead(BaseModel):
    friendship_id: int
    user_id: int
    display_name: str
    avatar_seed: str | None
    level: int
    xp_total: int
    status: str
    direction: str  # "incoming" | "outgoing" | "mutual"


class FriendsList(BaseModel):
    friends: list[FriendRead]
    incoming_requests: list[FriendRead]
    outgoing_requests: list[FriendRead]


class FriendRequestCreate(BaseModel):
    email: EmailStr


class FriendRespond(BaseModel):
    accept: bool


class FriendshipRead(ORMModel):
    id: int
    user_id: int
    friend_id: int
    status: str
    created_at: datetime


class ChallengeRead(BaseModel):
    code: str
    name: str
    description: str
    target: int
    progress: int
    complete: bool
