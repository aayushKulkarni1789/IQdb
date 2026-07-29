# ADR Review Manifest

- Status: completed
- Review date: 2026-07-29

## Review Summary

ADR review completed for this change.

## In-Force ADRs Reviewed

- `adr/0001-filter-subset-rank-taxonomy.md` — SubsetFilter vs RankFilter split (accepted)
- `adr/0002-lazy-sql-pushdown-candidatequery.md` — Lazy CandidateQuery (accepted)
- `adr/0003-reciprocal-rank-fusion.md` — Reciprocal Rank Fusion (accepted)

All three in-force ADRs remain compatible with this change. EXIF data ingestion does not alter the filter taxonomy, candidate query model, or fusion strategy.

## New Durable ADRs Created

- None — no major durable architectural decisions were introduced. The decisions in this change (Pillow EXIF extraction, strict tag pairing, GPS DMS-to-decimal conversion, module placement under `backend/app/search/`) are tactical implementation choices that do not establish new long-term architectural commitments.
