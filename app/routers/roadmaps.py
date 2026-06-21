"""Roadmaps router: list/create/detail, markdown import, topic toggle."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.models.enums import RoadmapSource
from app.models.roadmap import Roadmap
from app.schemas.roadmap import (
    PhaseRead,
    RoadmapCreate,
    RoadmapDetail,
    RoadmapImportRequest,
    RoadmapSummary,
    TopicRead,
    TopicToggleResult,
    TopicUpdate,
)
from app.services import roadmaps as roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])


def _summary(roadmap: Roadmap) -> RoadmapSummary:
    progress = roadmap_service.roadmap_progress(roadmap)
    summary = RoadmapSummary.model_validate(roadmap)
    summary.total_topics = progress.total
    summary.done_topics = progress.done
    summary.progress_pct = progress.pct
    return summary


def _detail(roadmap: Roadmap) -> RoadmapDetail:
    detail = RoadmapDetail.model_validate(_summary(roadmap).model_dump())
    phases: list[PhaseRead] = []
    for phase in roadmap.phases:
        topics = [TopicRead.model_validate(t) for t in phase.topics]
        done = sum(1 for t in phase.topics if t.done)
        phases.append(
            PhaseRead(
                id=phase.id,
                name=phase.name,
                duration_label=phase.duration_label,
                order_index=phase.order_index,
                topics=topics,
                done_count=done,
                total_count=len(topics),
                complete=bool(topics) and done == len(topics),
            )
        )
    detail.phases = phases
    return detail


@router.get("", response_model=list[RoadmapSummary])
async def list_roadmaps(current_user: CurrentUser, session: DbSession) -> list[RoadmapSummary]:
    roadmaps = await roadmap_service.list_roadmaps(session, current_user)
    return [_summary(r) for r in roadmaps]


@router.post("", response_model=RoadmapDetail, status_code=status.HTTP_201_CREATED)
async def create_roadmap(
    payload: RoadmapCreate, current_user: CurrentUser, session: DbSession
) -> RoadmapDetail:
    roadmap = Roadmap(
        user_id=current_user.id,
        title=payload.title,
        icon=payload.icon,
        color=payload.color,
        source=RoadmapSource.BUILTIN,
        is_dsa_linked=payload.is_dsa_linked,
    )
    session.add(roadmap)
    await session.flush()
    return await detail_response(session, current_user, roadmap.id)


@router.post("/import", response_model=RoadmapDetail, status_code=status.HTTP_201_CREATED)
async def import_roadmap(
    payload: RoadmapImportRequest, current_user: CurrentUser, session: DbSession
) -> RoadmapDetail:
    roadmap = await roadmap_service.import_roadmap(
        session,
        current_user,
        markdown=payload.markdown,
        icon=payload.icon,
        color=payload.color,
        is_dsa_linked=payload.is_dsa_linked,
    )
    return await detail_response(session, current_user, roadmap.id)


@router.get("/{roadmap_id}", response_model=RoadmapDetail)
async def get_roadmap(
    roadmap_id: int, current_user: CurrentUser, session: DbSession
) -> RoadmapDetail:
    return await detail_response(session, current_user, roadmap_id)


@router.patch("/{roadmap_id}/topics/{topic_id}", response_model=TopicToggleResult)
async def toggle_topic(
    roadmap_id: int,
    topic_id: int,
    payload: TopicUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> TopicToggleResult:
    outcome = await roadmap_service.toggle_topic(session, current_user, topic_id, payload.done)
    return TopicToggleResult(
        topic=TopicRead.model_validate(outcome.topic),
        phase_complete=outcome.phase_complete,
        roadmap_progress_pct=outcome.roadmap_pct,
        xp_awarded=outcome.xp_awarded,
        dsa_habit_credited=outcome.dsa_credited,
    )


async def detail_response(session: DbSession, user: CurrentUser, roadmap_id: int) -> RoadmapDetail:
    roadmap = await roadmap_service.get_roadmap(session, user, roadmap_id)
    return _detail(roadmap)
