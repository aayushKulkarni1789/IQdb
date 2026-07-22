from fastapi import HTTPException
from sqlmodel import Session

from app.crud import (
    append_filter_spec,
    create_search_session,
    finalize_search_session,
    get_search_session_by_id,
)
from app.models import SearchSession
from app.search.filter import CandidateQuery, RankFilter
from app.search.registry import UnknownFilterKindError, from_spec


def _build_candidate_query(specs):
    subset_filters = []
    rank_filters = []
    for spec in specs:
        f = from_spec(spec)
        if isinstance(f, RankFilter):
            rank_filters.append(f)
        else:
            subset_filters.append(f)
    return CandidateQuery(subset_filters, rank_filters)


def create_session(db: Session) -> SearchSession:
    return create_search_session(db)


def add_filter(db: Session, session_id: int, spec: dict) -> int:
    session = get_search_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Search session not found")
    if session.finalized:
        raise HTTPException(status_code=409, detail="Search session already finalized")
    try:
        f = from_spec(spec)
    except UnknownFilterKindError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not f.is_live:
        raise HTTPException(
            status_code=501,
            detail=f"Filter '{f.kind}' is not implemented",
        )
    session = append_filter_spec(db, session, spec)
    cq = _build_candidate_query(session.specs)
    return cq.candidate_count(db)


def finalize(db: Session, session_id: int, top_k: int = 100):
    session = get_search_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Search session not found")
    if session.finalized:
        raise HTTPException(status_code=409, detail="Search session already finalized")
    cq = _build_candidate_query(session.specs)
    results = cq.finalize(db, top_k)
    finalize_search_session(db, session)
    return len(results), results
