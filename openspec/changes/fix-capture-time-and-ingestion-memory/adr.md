# ADR Review Manifest

- Status: completed
- Review date: 2026-08-03

## Review Summary

ADR review completed for this change. The change fixes defects in existing ingestion behavior (EXIF sub-IFD lookup, batch memory release, embedding/file pairing) and introduces no new architectural commitment, technology, boundary, or contract. No prior ADR is diverged from or superseded.

## In-Force ADRs Reviewed

- `0001-filter-subset-rank-taxonomy` — **Filter** taxonomy (SubsetFilter vs RankFilter); unaffected by ingestion-time EXIF extraction.
- `0002-lazy-sql-pushdown-candidatequery` — Lazy SQL push-down via **CandidateQuery**; unaffected, no query path changed.
- `0003-reciprocal-rank-fusion` — **Reciprocal Rank Fusion** (`k=60`); unaffected, no search/finalize path changed.

## New Durable ADRs Created

- None — no major durable architectural decisions were introduced by this change; all decisions in design.md are tactical bug-fix implementation choices.
