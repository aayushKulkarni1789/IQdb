from typing import Any

from sqlalchemy import ColumnElement, func, literal, select
from sqlalchemy.sql import Select
from sqlmodel import Session

from app.models import CLIP_Embedding, Image


RRF_K = 60


class Filter:
    """Base class for all search filters.

    A filter is reconstructed from a JSON ``spec`` via :meth:`from_spec` and can
    serialize itself back to a spec via :meth:`to_spec`. ``kind`` is the stable
    registry key; ``is_live`` advertises whether the filter can actually execute.
    """

    kind: str = ""
    is_live: bool = True

    def to_spec(self) -> dict[str, Any]:
        return {"kind": self.kind}

    @classmethod
    def from_spec(cls, spec: dict[str, Any]) -> "Filter":
        return cls()


class SubsetFilter(Filter):
    """A filter that narrows the candidate set via a SQL ``WHERE`` predicate."""

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

    def finalize(self, db: Session, top_k: int) -> list[tuple[int, float | None]]:
        pool = self._universe.subquery()

        if not self._rank_filters:
            # No rank filters: skip RRF, return id-ordered hits with score null.
            stmt = (
                select(pool.c.id, literal(None).label("score"))
                .select_from(pool)
                .order_by(pool.c.id)
                .limit(top_k)
            )
            return [(row.id, None) for row in db.exec(stmt)]

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
            select(combined_sub.c.id, score_expr.label("score"))
            .group_by(combined_sub.c.id)
            .order_by(score_expr.desc())
            .limit(top_k)
        )
        return [(row.id, float(row.score)) for row in db.exec(stmt)]
