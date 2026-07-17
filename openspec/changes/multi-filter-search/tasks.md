## 1. Persistence — SearchSession model & migration

- [ ] 1.1 Add `SearchSession` SQLModel table to `backend/app/models.py` (`id` PK, `specs JSONB`, `finalized bool`, `created_at timestamptz`) per `design.md` Migration Plan.
- [ ] 1.2 Generate and apply the migration against the containerized Postgres: first `docker compose up -d`, then `make migrate msg="add search session"` to autogenerate, then `make upgrade` (`docker compose exec backend alembic upgrade head`) to apply. Rollback = `alembic downgrade -1` / drop the table. No backfill required.
- [ ] 1.3 Add session CRUD functions to `backend/app/crud.py`: `create_search_session`, `get_search_session_by_id`, `append_filter_spec` (JSONB append), `finalize_search_session` (flip `finalized`).

## 2. Filter abstraction — `backend/app/search/filter.py`

- [ ] 2.1 Create `backend/app/search/filter.py` with `Filter` base, `SubsetFilter.build_predicate() -> ColumnElement`, `RankFilter.build_rank_cte(candidates) -> Select` returning `(id, row_number)` per `design.md` D1.
- [ ] 2.2 Implement `CandidateQuery` (D2): universe `select(Image.id)`, append subset predicates to `WHERE`, build rank CTEs, expose `candidate_count` (`COUNT(*)` over phase-1 subset `Select`) and `finalize(top_k)`.
- [ ] 2.3 Keep the candidate set a lazy `Select`; ensure no image IDs materialize into Python until the final `LIMIT K`.

## 3. Filters — CLIP (impl) and stubs

- [ ] 3.1 Implement `backend/app/search/filters/clip.py` `ClipRank`: store text query in spec, recompute vector via `get_text_embeddings` at `from_spec`, rank via `CLIP_Embedding.embedding.cosine_distance(vec)` over the indexed column (D5).
- [ ] 3.2 Add `backend/app/search/filters/datetime.py` `DatetimeFilter` stub: `build_predicate` raises `NotImplementedError` documenting `EXIF between` intent (D6).
- [ ] 3.3 Add `backend/app/search/filters/geo.py` `GeoFilter` stub: `build_predicate` raises `NotImplementedError` documenting `ST_DWithin`/haversine intent.
- [ ] 3.4 Add `backend/app/search/filters/face.py` `FaceFilter` stub: `build_predicate` raises `NotImplementedError` documenting face threshold intent.

## 4. Registry — `backend/app/search/registry.py`

- [ ] 4.1 Implement `registry.py`: name -> filter class map; `ClipRank` advertised as live; `DatetimeFilter`/`GeoFilter`/`FaceFilter` advertised as not-implemented; `from_spec` validates unknown kinds.
- [ ] 4.2 Expose a registry query so the agent can inspect which filters are live vs unimplemented (spec: "registry advertises which filters are live").

## 5. Orchestrator & schemas — `orchestrator.py`, `schemas.py`

- [ ] 5.1 Implement `backend/app/search/orchestrator.py`: `create_session`, `add_filter` (append spec, return `candidate_count` from phase-1 subset query), `finalize` (D3 two-phase: bucket specs by kind, phase-1 intersect subsets, phase-2 RRF fuse `k=60`).
- [ ] 5.2 Implement RRF mechanics (D4): `union_all` rank CTEs -> `SUM(weight/(k+rank)) GROUP BY id ORDER BY score DESC LIMIT top_k`; skip RRF when zero rank filters and return id-ordered hits with `score: null`.
- [ ] 5.3 Enforce `409 Conflict` when `/filters` or `/finalize` is called on a `finalized` session (D7).
- [ ] 5.4 Enforce add-time `501 Not Implemented` rejection for stub filters; spec must not be appended (D6).
- [ ] 5.5 Create `backend/app/search/schemas.py` with request/response models; `finalize` response uses `number_of_images_in_output`; filter-add response uses `candidate_count` (D8).

## 6. API routes — `backend/app/search/routes.py`

- [ ] 6.1 Implement `routes.py` with `POST /sessions`, `POST /sessions/{id}/filters`, `POST /sessions/{id}/finalize` wired to the orchestrator.
- [ ] 6.2 Include the new search router in `backend/app/api/v1/main.py` (and confirm existing `utils`/`uploads` routers still load).

## 7. Tests & validation (fresh pytest suite)

- [ ] 7.1 Rewrite `backend/tests/conftest.py`: drop the in-memory SQLite engine (it cannot handle `VECTOR(512)` / HNSW / `JSONB`). Use the real Postgres engine from `app.core.db.engine`, require `docker compose up` + schema present, and provide `db_session` (truncate-per-test isolation) and `client` (override `get_db`) fixtures. Build schema in the docker Postgres via `SQLModel.metadata.create_all` for fast, isolated runs.
- [ ] 7.2 Keep `backend/tests/test_uploads.py`: port the valid upload-behavior tests (they currently error only because of the SQLite conftest) so the suite runs green.
- [ ] 7.3 Add `backend/tests/test_search.py` covering spec scenarios in `specs/image-search/spec.md`: session lifecycle (create / apply in any order / finalize / terminal `409`), `candidate_count` subset-only, RRF skipped with `score: null` when zero rank filters, CLIP rank end-to-end (mock the embedding model), stub `501` at add-time, and registry liveness advertisement.
- [ ] 7.4 Document the test command: `docker compose up -d` -> `make upgrade` (or `create_all`) -> `pytest backend/tests`.
- [ ] 7.5 Run `openspec validate multi-filter-search --type change --strict` and ensure it passes before archive.
