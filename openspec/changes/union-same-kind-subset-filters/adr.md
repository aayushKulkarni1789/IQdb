# ADR Review Manifest

- Status: completed
- Review date: 2026-08-28

## Review Summary

ADR review completed for this change. No major durable architectural decisions were introduced — this change refines how `CandidateQuery` composes subset predicates, working within the existing taxonomy (ADR-0001), lazy push-down (ADR-0002), and RRF (ADR-0003) decisions.

## In-Force ADRs Reviewed

- ADR-0001: Filter taxonomy (SubsetFilter vs RankFilter split) — this change operates within the SubsetFilter composition path
- ADR-0002: Lazy SQL push-down via CandidateQuery — predicate composition stays in the lazy Select, no materialization change
- ADR-0003: Reciprocal Rank Fusion — unchanged, phase-2 is unaffected
- ADR-0004: Cleanup Sweep — unrelated, reviewed for completeness

## New Durable ADRs Created

- None — the union-then-intersect composition is a tactical refinement of CandidateQuery, not a new architectural commitment. The grouping strategy (by FilterKind) follows naturally from ADR-0001's FilterKind enum.
