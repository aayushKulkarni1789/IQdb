# Filter taxonomy: SubsetFilter vs RankFilter split

## Context and Problem Statement

The Image Search capability needs to combine multiple filters (datetime, geo, face, CLIP text) into a single query. These filters have fundamentally different output shapes: some narrow the candidate set by boolean membership (datetime, geo, face), while CLIP produces a continuous relevance score. We must decide how to model filters so that adding a new filter is uniform and the orchestrator can fuse them correctly in a two-phase plan.

## Considered Options

- Single score-and-threshold model where every filter emits a rank score; boolean filters convert to a 0/1 score and a threshold.
- Split taxonomy: `SubsetFilter` emits a `WHERE` predicate, `RankFilter` emits a rank CTE fused by Reciprocal Rank Fusion.
- Fully generic "predicate + optional score" filter where each filter decides at runtime how it participates.

## Decision Outcome

Chosen option: "Split taxonomy: `SubsetFilter` emits a `WHERE` predicate, `RankFilter` emits a rank CTE". Each filter is responsible for exactly one output shape. `SubsetFilter.build_predicate() -> ColumnElement` produces a commutative `WHERE` clause; `RankFilter.build_rank_cte(candidates) -> Select` returns `(id, row_number)`. The orchestrator buckets specs by `kind` at finalize time: all subsets compose phase-1 (intersect), all ranks compose phase-2 (RRF).

### Consequences

- Good, because membership narrowing and continuous scoring stay clean; no awkward predicate-to-rank conversions.
- Good, because new filters only need to pick a shape and implement one method, keeping the tool/contract surface uniform for the agent.
- Bad, because the taxonomy is a hard boundary: a filter that is both boolean and scored must be modeled as two specs, adding design care for future filters.
