## Why

The backend ingests images and stores CLIP embeddings (`CLIP_Embedding.embedding VECTOR(512)` with an **HNSW cosine index**), but there is no query path that lets an LLM agent retrieve images by combining filters. A text-query-driven image search needs to combine **subset filters** (datetime, geo, face — narrow the candidate set via definite membership) with **rank filters** (CLIP similarity — continuous scores fused by **Reciprocal Rank Fusion**). This change builds that ecosystem: a Filter abstraction, a session that accumulates filter calls, and an orchestrator that enforces the required two-phase rule (all subsets first, then all ranks). CLIP is implemented end-to-end; datetime/geo/face are registered stubs so the contract and tool surface exist without depending on not-yet-built ingestion (EXIF, PostGIS, face models).

## What Changes

- Add a `Filter` abstraction split by output shape: `SubsetFilter` (contributes a SQL `WHERE` predicate) and `RankFilter` (contributes a rank CTE combined via RRF at finalize). Filters use lazy SQL push-down — the candidate set is a `Select`, never materialized as Python IDs until `LIMIT K`.
- Implement `ClipRank`: text query -> `get_text_embeddings` (existing `core/clip.py`) -> **pgvector** `cosine_distance` ranking over `CLIP_Embedding`, reusing the existing HNSW cosine index.
- Add `DatetimeFilter`, `GeoFilter`, `FaceFilter` as registered template stubs (`build_predicate` raises `NotImplementedError`; the unified endpoint rejects them with `501` until implemented).
- Add `SearchSession` persistence: a Postgres row holding an ordered JSONB `specs` log, a `finalized` boolean, and `created_at`. No `phase` field — phase is derived at finalize.
- Add search API surface: `POST /sessions`, `POST /sessions/{id}/filters` (unified, accepts any filter kind in any order), `POST /sessions/{id}/finalize`.
- Orchestrator enforces phase-1 (intersect all subset predicates) then phase-2 (build rank CTEs, RRF-fuse with `k=60`). RRF is skipped entirely when there are zero rank filters.
- No LLM-agent code is written; only the tool-call surface an agent would reference later.

## Capabilities

### New Capabilities
- `image-search`: tool-driven multi-filter image search — session lifecycle (create / apply filters / finalize), subset filters that narrow via `WHERE`, rank filters buffered then fused by RRF, and a **Finalize** that returns **Top-K** hits. CLI/agent calls filters in any order; phase is enforced only inside finalize.

### Modified Capabilities
<!-- none — no existing spec-level behaviour changes -->

## Impact

- **New code** (`backend/app/search/`): `filter.py` (abstraction + `CandidateQuery`), `filters/clip.py` (implemented), `filters/datetime.py`, `filters/geo.py`, `filters/face.py` (stubs), `registry.py`, `orchestrator.py`, `schemas.py`, `routes.py`.
- **Edited**: `models.py` (add `SearchSession`), `crud.py` (session CRUD), `api/v1/main.py` (include router), `alembic/versions/` (migration).
- **Depends on**: existing pgvector extension, `CLIP_Embedding` table + HNSW index, and `get_text_embeddings` in `core/clip.py` — all already present.
- **No new infra**: no Redis; session state is a small Postgres JSONB row. Stack unchanged (Postgres 18 + pgvector, single sync engine).
- **Deferred (not in this change)**: EXIF capture-time extraction, geo columns/PostGIS, face detection + embedding model + table, the LLM agent itself, auth, pagination, persisting results.
