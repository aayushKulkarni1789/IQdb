from datetime import datetime
from typing import Any

from pydantic import ConfigDict
from sqlmodel import SQLModel

from app.search.filter import FilterKind


class SearchHit(SQLModel):
    id: int
    uri: str
    score: float | None = None


class SessionCreateResponse(SQLModel):
    id: int
    finalized: bool = False
    created_at: datetime | None = None


class FilterAddResponse(SQLModel):
    candidate_count: int


class FinalizeResponse(SQLModel):
    number_of_images_in_output: int
    hits: list[SearchHit]


class FinalizeRequest(SQLModel):
    top_k: int = 100


class FilterAddRequest(SQLModel):
    """Unified filter-add body. ``kind`` selects the filter; remaining fields
    are passed through to the filter implementation as the spec.
    to_spec returns the json body of the request, hence the request should follow the
    respective filter syntax"""

    # Strictly typed so pydantic rejects unknown kinds at request validation
    # with 422 and documents the valid set in OpenAPI (design D5).
    kind: FilterKind

    model_config = ConfigDict(extra="allow")

    def to_spec(self) -> dict[str, Any]:
        return self.model_dump()


class FilterInfo(SQLModel):
    kind: str
    live: bool
