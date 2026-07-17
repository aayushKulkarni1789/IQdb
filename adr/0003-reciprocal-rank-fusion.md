# Reciprocal Rank Fusion for multi-rank filters

## Context and Problem Statement

When a search session has multiple rank filters (e.g. CLIP plus future scored filters), their scores are not directly comparable across modalities. We need a fusion strategy that combines ranked lists without normalizing heterogeneous scores, and that degrades gracefully when there are zero rank filters.

## Considered Options

- Weighted linear combination of normalized scores (requires comparable, normalized scores per filter).
- Reciprocal Rank Fusion: `score(id) = Σ weight / (k + rank_i(id))` with `k=60`, unioning rank CTEs and `GROUP BY id ORDER BY score DESC LIMIT top_k`.

## Decision Outcome

Chosen option: "Reciprocal Rank Fusion with `k=60`". Each rank filter becomes a CTE returning `(id, row_number)`; they are `union_all`ed, summed as `SUM(weight/(k+rank))`, grouped by `id`, and ordered descending for the top-K. When zero rank filters exist, finalize returns the narrowed set ordered by `Image.id` with `score: null` (no fabricated relevance). Finalize derives the phase at runtime by bucketing specs; the `RRF skipped if 0 ranks` behavior is unconditional.

### Consequences

- Good, because fusion needs no score normalization across modalities and is a single SQL pass.
- Good, because zero-rank sessions still return a deterministic, honest result with no fake score.
- Bad, because RRF weights are currently uniform/implicit; per-filter weights are not yet configurable and would need a later ADR if differentiated ranking is required.
