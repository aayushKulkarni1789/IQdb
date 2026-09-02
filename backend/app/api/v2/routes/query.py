from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.search.agent.llm import invoke as agent_invoke

from app.api.deps import SessionDep
from app.search.query import finalize as finalize_filters

router = APIRouter()


class QueryRequest(BaseModel):
    user_text: str
    top_k: int = 100


class SearchHit(BaseModel):
    id: int
    uri: str
    score: float | None = None


class QueryResponse(BaseModel):
    number_of_images_in_output: int
    hits: list[SearchHit]


@router.post("/query", response_model=QueryResponse)
def query_search(payload: QueryRequest, db: SessionDep):
    # Lazy import to avoid circular and to allow testing without LLM
    from app.search.agent.llm import invoke as agent_invoke

    try:
        result = agent_invoke(payload.user_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filters = result.get("filters", []) if isinstance(result, dict) else []
    if not filters:
        raise HTTPException(status_code=422, detail="No filters derived from query")
    count, hits = finalize_filters(db, filters, payload.top_k)
    return QueryResponse(
        number_of_images_in_output=count,
        hits=[SearchHit(id=h[0], uri=h[1], score=h[2]) for h in hits],
    )
