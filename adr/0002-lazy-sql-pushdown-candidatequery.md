# Lazy SQL push-down via CandidateQuery

## Context and Problem Statement

The backend stores `CLIP_Embedding.embedding VECTOR(512)` with an HNSW cosine index. When a search session accumulates filters, we must avoid materializing candidate image IDs into Python until the final `LIMIT K`, or we lose index push-down, risk memory blow-up at scale, and turn RRF fusion into a Python loop. We need a query model that keeps the candidate set lazy and executable as a single SQL pass.

## Considered Options

- Materialize the candidate ID set in Python after each filter and intersect/rank in application code.
- Lazy `CandidateQuery`: universe is `select(Image.id)`; subset predicates append to `WHERE`; rank filters become CTEs fused at finalize; only the final `LIMIT K` returns IDs to Python.

## Decision Outcome

Chosen option: "Lazy `CandidateQuery`". The candidate set is a `Select`, never a Python list of IDs, until the final top-K read. `candidate_count` is computed as `COUNT(*)` over the phase-1 `Select` built from subset predicates only; rank specs are excluded from this count and apply last. This preserves pgvector index push-down through `cosine_distance` and keeps RRF fusion in SQL.

### Consequences

- Good, because index push-down is retained for both subset predicates and the CLIP rank CTE.
- Good, because no image IDs materialize into Python until the final `LIMIT K`, bounding memory.
- Bad, because the query builder is more complex than eager in-Python intersection; correctness depends on the SQL dialect and planner respecting the HNSW index inside fused CTEs.
