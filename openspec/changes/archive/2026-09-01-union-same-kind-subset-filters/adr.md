# ADR Review Manifest

- Status: completed
- Review date: 2026-08-28

## Review Summary

ADR review completed for this change. One new durable architectural decision was introduced: composing same-kind SubsetFilter predicates via union (OR) before intersecting across kinds (ADR-0006).

## In-Force ADRs Reviewed

- ADR-0001: Filter taxonomy (SubsetFilter vs RankFilter split) — this change operates within the SubsetFilter composition path
- ADR-0002: Lazy SQL push-down via CandidateQuery — predicate composition stays in the lazy Select, no materialization change
- ADR-0003: Reciprocal Rank Fusion — unchanged, phase-2 is unaffected
- ADR-0004: Cleanup Sweep — unrelated, reviewed for completeness

## New Durable ADRs Created

- ADR-0006: Union same-kind subset filters before cross-kind intersection — captures the decision to group SubsetFilter predicates by FilterKind and compose intra-kind with OR, cross-kind with AND.
