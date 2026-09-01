# Union same-kind subset filters before cross-kind intersection

## Context and Problem Statement

CandidateQuery composes SubsetFilter predicates via AND (intersection). This is correct for cross-kind filters (datetime AND geo), but wrong for same-kind filters: two datetime ranges (Jan-Mar, Jun-Aug) intersect to zero results, when the natural semantics is union (OR).

## Considered Options

- Compose all subset predicates as AND (status quo) — correct for cross-kind, wrong for same-kind.
- Group by FilterKind, compose same-kind with OR, cross-kind with AND — matches natural semantics.
- Move grouping to orchestrator — changes CandidateQuery constructor signature; grouping is an implementation detail.

## Decision Outcome

Chosen option: "Group by FilterKind, compose same-kind with OR", because the FilterKind enum (ADR-0001) is the stable grouping key, and SQLAlchemy's `or_()` produces `(pred1 OR pred2) AND (pred3 OR pred4)` via operator precedence.

### Consequences

- Good, because same-kind filters now match natural user intent ("Jan-Mar OR Jun-Aug").
- Good, because cross-kind composition is unchanged (multiple WHERE clauses = AND).
- Bad, because OR chain length grows linearly with same-kind filter count (PostgreSQL handles this efficiently at expected counts).
