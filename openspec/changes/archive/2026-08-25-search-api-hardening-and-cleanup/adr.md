# ADR Review Manifest

- Status: completed
- Review date: 2026-08-23

## Review Summary

ADR review completed for this change.

## In-Force ADRs Reviewed

- `adr/0001-filter-subset-rank-taxonomy.md` - the subset/rank classification this change's `FilterKind` enum formalizes; not superseded, extended only.
- `adr/0002-lazy-sql-pushdown-candidatequery.md` - D7's URI join stays inside the final top-K statement, preserving lazy push-down; no divergence.
- `adr/0003-reciprocal-rank-fusion.md` - RRF fusion untouched; the join appends to both finalize paths without altering scoring.

## New Durable ADRs Created

- `adr/0004-cleanup-sweep-for-finished-entities.md` - in-process asyncio cleanup sweep with derived, unpersisted schedule and unconditional deletion of finished entities (design D1-D4). Establishes the long-term pattern for entity lifecycle cleanup; future `UPLOAD_ROOT` file deletion must build on it.

Decisions not promoted to ADRs (tactical, no long-term commitment beyond this change): `FilterKind` StrEnum and strict request validation (type-safety refinement within ADR-0001's taxonomy), pydantic spec models with `InvalidFilterSpecError.from_validation` (error-surface detail), finalize URI join (preserves ADR-0002 as-is), ingestion summary log format (operational logging).
