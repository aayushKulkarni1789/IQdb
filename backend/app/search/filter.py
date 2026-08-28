from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError
from sqlalchemy import ColumnElement, func, literal, select
from sqlalchemy.sql import Select
from sqlmodel import Session

from app.models import CLIP_Embedding, Image


RRF_K = 60


# Closed enumeration of filter kinds (design D5). Persisted JSONB specs store
# plain strings that round-trip through this StrEnum unchanged.
class FilterKind(StrEnum):
    CLIP = "clip"
    DATETIME = "datetime"
    GEO = "geo"
    FACE = "face"


class InvalidFilterSpecError(ValueError):
    """Raised when a filter spec has a valid kind but malformed fields."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @classmethod
    def from_validation(
        cls,
        kind: FilterKind,
        exc: ValidationError,
        fmt: str,
        example: Any,
    ) -> "InvalidFilterSpecError":
        # Single formatter producing problem list, expected format, and a
        # concrete example so agent clients get a self-service recovery path.
        problems = "; ".join(
            "{}: {}".format(".".join(str(loc) for loc in err["loc"]), err["msg"])
            for err in exc.errors()
        )
        return cls(
            f"Invalid {kind.value} filter spec. Problems: {problems}. "
            f"Expected format: {fmt}. Example: {example}"
        )


# While creating a new filter, it is recommend to overload all the given methods and attributes.
class Filter:
    """Base class for all search filters.

    A filter is reconstructed from a JSON ``spec`` via :meth:`from_spec` and can
    serialize itself back to a spec via :meth:`to_spec`. ``kind`` is the stable
    registry key; ``is_live`` advertises whether the filter can actually execute.
    Subclasses declare a pydantic ``spec_model`` validating their spec shape and
    a ``SPEC_FORMAT``/``SPEC_EXAMPLE`` pair used for actionable error messages.
    """

    kind: ClassVar[FilterKind]
    spec_model: ClassVar[type[BaseModel]]
    SPEC_FORMAT: ClassVar[str] = ""
    SPEC_EXAMPLE: ClassVar[Any] = {}
    is_live: bool = True

    # return the spec dictionary of this filter
    def to_spec(self) -> dict[str, Any]:
        return {"kind": self.kind}

    # create the filter object from a validated spec model
    @classmethod
    def from_spec(cls, spec_model: Any) -> "Filter":
        return cls()


# A subset filter includes a "subset" of all images that satisfy a certain criteria.
class SubsetFilter(Filter):
    """A filter that narrows the candidate set via a SQL ``WHERE`` predicate."""

    # This function will contain the logic of creating the WHERE clause.
    def build_predicate(self) -> ColumnElement:
        raise NotImplementedError


class RankFilter(Filter):
    """A filter that contributes a ranked CTE fused by RRF at finalize."""

    weight: float = 1.0

    def build_rank_cte(self, candidates: Select) -> Select:
        """Return a ``Select`` of ``(id, rank, weight)`` over ``candidates``.

        ``candidates`` is a lazy ``Select`` projecting ``Image.id`` already
        narrowed by all subset predicates (phase-1 pool).
        """
        raise NotImplementedError


# This is the main orchestrator that converts a list of ranked and subset filters into an SQL ORM expression and return the images
class CandidateQuery:
    """Lazy SQL push-down of the candidate set (design D2).

    The universe is ``select(Image.id)``; subset predicates are appended to
    ``WHERE``; rank filters become CTEs fused only at :meth:`finalize`. No image
    IDs materialize into Python until the final ``LIMIT K``.
    """

    def __init__(
        self,
        subset_filters: list[SubsetFilter],
        rank_filters: list[RankFilter],
    ) -> None:
        universe = select(Image.id)
        for f in subset_filters:
            universe = universe.where(f.build_predicate())
        self._universe = universe
        self._rank_filters = rank_filters

    def candidate_count(self, db: Session) -> int:
        """``COUNT(*)`` over the phase-1 subset ``Select`` only (D8)."""
        stmt = select(func.count()).select_from(self._universe.subquery())
        return int(db.exec(stmt).scalar_one())

    # Finalize the filters and return the resultant image set
    def finalize(self, db: Session, top_k: int) -> list[tuple[int, str, float | None]]:
        pool = self._universe.subquery()

        if not self._rank_filters:
            # No rank filters: skip RRF, return id-ordered hits with score null.
            # PK join into image stays inside this final top-K statement (D7).
            stmt = (
                select(pool.c.id, Image.uri, literal(None).label("score"))
                .join(Image, Image.id == pool.c.id)
                .order_by(pool.c.id)
                .limit(top_k)
            )
            return [(row.id, row.uri, None) for row in db.exec(stmt)]

        # Phase-2: build each rank CTE, then fuse via RRF (D4).
        rank_ctes = [rf.build_rank_cte(self._universe).cte() for rf in self._rank_filters]
        combined = select(
            rank_ctes[0].c.id,
            rank_ctes[0].c.rank,
            rank_ctes[0].c.weight,
        )
        for cte in rank_ctes[1:]:
            combined = combined.union_all(select(cte.c.id, cte.c.rank, cte.c.weight))
        combined_sub = combined.subquery()
        score_expr = func.sum(combined_sub.c.weight / (RRF_K + combined_sub.c.rank))
        stmt = (
            select(combined_sub.c.id, Image.uri, score_expr.label("score"))
            .join(Image, Image.id == combined_sub.c.id)
            .group_by(combined_sub.c.id, Image.uri)
            .order_by(score_expr.desc())
            .limit(top_k)
        )
        # Execute the finalized query and return the results.
        return [(row.id, row.uri, float(row.score)) for row in db.exec(stmt)]
