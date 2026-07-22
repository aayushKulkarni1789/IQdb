# ADR Review Manifest

- Status: completed
- Review date: 2026-07-17

## Review Summary

ADR review completed for this change. The design introduces durable architectural commitments that affect future changes beyond this one (the filter taxonomy, lazy SQL push-down, and rank fusion strategy). Three repository-level ADRs were created under `adr/` to capture them. No previously accepted ADRs existed (no `adr/` folder was present), so nothing was superseded.

## In-Force ADRs Reviewed

- None prior - `adr/` had no in-force ADRs before this change.

## New Durable ADRs Created

- `adr/0001-filter-subset-rank-taxonomy.md` - Split filter model: `SubsetFilter` emits a `WHERE` predicate, `RankFilter` emits a rank CTE. (design D1)
- `adr/0002-lazy-sql-pushdown-candidatequery.md` - Candidate set stays a `Select`; IDs materialize into Python only at final `LIMIT K`. (design D2)
- `adr/0003-reciprocal-rank-fusion.md` - RRF (`k=60`) fuses rank CTEs; zero-rank sessions return id-ordered results with `score: null`. (design D4)

Design decisions D3, D5, D6, D7, D8 were reviewed and judged tactical/contract-level for this change (phase derived not stored, CLIP vector laziness, stub fail-fast, terminal session, response field naming) and were not promoted to repository-level ADRs.
