from sqlmodel import Session

from app.search.filter import CandidateQuery, Filter, RankFilter, SubsetFilter


def finalize(
    db: Session, filters: list[Filter], top_k: int = 100
) -> tuple[int, list[tuple[int, str, float | None]]]:
    """Partition filters and delegate to CandidateQuery (no SearchSession).

    Mirrors orchestrator._build_candidate_query but operates on Filter objects.
    """
    subset_filters: list[SubsetFilter] = []
    rank_filters: list[RankFilter] = []
    for f in filters:
        if isinstance(f, RankFilter):
            rank_filters.append(f)
        elif isinstance(f, SubsetFilter):
            subset_filters.append(f)
        else:
            # Fallback: treat any RankFilter subclass, otherwise subset
            if isinstance(f, RankFilter):
                rank_filters.append(f)
            else:
                subset_filters.append(f)
    cq = CandidateQuery(subset_filters, rank_filters)
    results = cq.finalize(db, top_k)
    return len(results), results
