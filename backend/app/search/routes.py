from fastapi import APIRouter

from app.api.deps import SessionDep
from app.search.orchestrator import add_filter, create_session, finalize
from app.search.registry import list_filters
from app.search.schemas import (
    FilterAddRequest,
    FilterAddResponse,
    FilterInfo,
    FinalizeRequest,
    FinalizeResponse,
    SearchHit,
    SessionCreateResponse,
)

router = APIRouter(tags=["search"])


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_search_session_route(db: SessionDep) -> SessionCreateResponse:
    session = create_session(db)
    return SessionCreateResponse(
        id=session.id,
        finalized=session.finalized,
        created_at=session.created_at,
    )


@router.post("/sessions/{session_id}/filters", response_model=FilterAddResponse)
def add_filter_route(
    session_id: int,
    body: FilterAddRequest,
    db: SessionDep,
) -> FilterAddResponse:
    spec = body.to_spec()
    candidate_count = add_filter(db, session_id, spec)
    return FilterAddResponse(candidate_count=candidate_count)


@router.post("/sessions/{session_id}/finalize", response_model=FinalizeResponse)
def finalize_route(
    session_id: int,
    body: FinalizeRequest,
    db: SessionDep,
) -> FinalizeResponse:
    n, hits = finalize(db, session_id, top_k=body.top_k)
    return FinalizeResponse(
        number_of_images_in_output=n,
        hits=[SearchHit(id=image_id, uri=uri, score=score) for image_id, uri, score in hits],
    )


@router.get("/filters", response_model=list[FilterInfo])
def list_filters_route() -> list[FilterInfo]:
    return [FilterInfo(kind=f["kind"], live=f["live"]) for f in list_filters()]
