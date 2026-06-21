"""Community router: leaderboard, friends, challenges."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.community import (
    ChallengeRead,
    FriendRequestCreate,
    FriendRespond,
    FriendshipRead,
    FriendsList,
    LeaderboardEntryRead,
    LeaderboardRead,
)
from app.services import community as community_service

router = APIRouter(tags=["Community"])


@router.get("/leaderboard", response_model=LeaderboardRead)
async def leaderboard(
    current_user: CurrentUser,
    session: DbSession,
    scope: Literal["league", "friends", "global"] = Query(default="global"),
) -> LeaderboardRead:
    board = await community_service.leaderboard(session, current_user, scope)
    return LeaderboardRead(
        scope=scope,
        entries=[LeaderboardEntryRead.model_validate(e) for e in board.entries],
        my_rank=board.my_rank,
    )


@router.get("/friends", response_model=FriendsList)
async def list_friends(current_user: CurrentUser, session: DbSession) -> FriendsList:
    friends, incoming, outgoing = await community_service.list_friends(session, current_user)
    return FriendsList(friends=friends, incoming_requests=incoming, outgoing_requests=outgoing)


@router.post("/friends", response_model=FriendshipRead, status_code=status.HTTP_201_CREATED)
async def add_friend(
    payload: FriendRequestCreate, current_user: CurrentUser, session: DbSession
) -> FriendshipRead:
    friendship = await community_service.send_request(session, current_user, payload.email)
    return FriendshipRead.model_validate(friendship)


@router.post("/friends/{friendship_id}/respond", response_model=FriendsList)
async def respond_friend(
    friendship_id: int,
    payload: FriendRespond,
    current_user: CurrentUser,
    session: DbSession,
) -> FriendsList:
    await community_service.respond_request(session, current_user, friendship_id, payload.accept)
    friends, incoming, outgoing = await community_service.list_friends(session, current_user)
    return FriendsList(friends=friends, incoming_requests=incoming, outgoing_requests=outgoing)


@router.get("/challenges", response_model=list[ChallengeRead])
async def challenges(current_user: CurrentUser, session: DbSession) -> list[ChallengeRead]:
    return await community_service.weekly_challenges(session, current_user)
