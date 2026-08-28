# Tasks: search-api-hardening-and-cleanup

## 1. Ingestion summary logging

- [x] 1.1 Add summary counters to `backend/app/tasks.py` `process_upload_embeddings`: wrap the task body in `time.monotonic()` timing and count per batch — `total` (files seen), `opened_ok`, `written_to_db` (rows actually committed), and non-NULL persistence counts for `file_size`, `dimensions` (width AND height both persisted), `capture_time`, and `gps` (latitude AND longitude both persisted)
- [x] 1.2 Emit one INFO summary line at successful job completion reporting all counters, elapsed seconds, and `status=completed`
- [x] 1.3 Emit a partial INFO summary line with counters-so-far and `status=failed` in the exception handler before the job is marked discarded
- [x] 1.4 Add tests in `tests/test_uploads.py` (or a new test module) covering: full summary on success with varying EXIF completeness, grouped-field counting (dimensions/gps require all constituent columns non-NULL), unreadable files counted in `total` but excluded from `opened_ok`/`written_to_db`, and the failed-path partial summary — run via `make test`

## 2. Cleanup sweep

- [x] 2.1 Create new module `backend/app/core/cleanup.py` exposing a directly callable sweep-pass function taking a DB session that unconditionally deletes every finalized `SearchSession` row and every terminal `UploadJob` row (status COMPLETED or DISCARD); no retention-age check; return/log deleted-row counts
- [x] 2.2 Log per pass: INFO when rows were deleted, DEBUG for an empty pass; keep the physical deletion of `UPLOAD_ROOT/<job_id>/` as commented-out code with a note naming the multi-worker directory-race concern that must be resolved first
- [x] 2.3 Create a FastAPI lifespan handler in `backend/app/main.py` that starts an asyncio loop shortly after boot (first pass fires soon after startup), repeats every `SWEEP_INTERVAL_MINUTES` computed in memory (`next_pass = last_pass + interval`, never persisted), cancels the task on shutdown, and survives DB outages via per-pass try/except logging WARNING and retrying next tick
- [x] 2.4 Add `SWEEP_INTERVAL_MINUTES: int = 1440` to `backend/app/core/config.py` `Settings` and document it in `.env.example`
- [x] 2.5 Add tests invoking the sweep-pass function directly (no timer waits): finalized sessions are deleted while open sessions survive; completed and discarded jobs are deleted while pending/processing jobs survive; a DB-failure pass logs WARNING without raising

## 3. FilterKind StrEnum and strict request validation

- [x] 3.1 Define `class FilterKind(StrEnum)` with CLIP/DATETIME/GEO/FACE in `backend/app/search/filter.py`; change each filter class in `backend/app/search/filters/*.py` to declare `kind: ClassVar[FilterKind]`
- [x] 3.2 Convert `backend/app/search/registry.py` to key off `FilterKind`; `from_spec` converts the incoming spec string via `FilterKind(value)` before lookup so unknown values raise the existing 422-mapped error path (never a silent `KeyError`); verify persisted string specs still round-trip unchanged (StrEnum)
- [x] 3.3 Change `FilterAddRequest.kind` to `FilterKind` in `backend/app/search/schemas.py` so pydantic rejects unknown kinds at request validation with 422 and documents the valid set in OpenAPI
- [x] 3.4 Add tests covering: unknown kind returns 422 listing valid values and appends no spec; existing persisted specs remain valid after strict typing (no data migration)

## 4. Actionable filter-spec validation errors

- [x] 4.1 Give each filter class in `backend/app/search/filters/*.py` a pydantic spec model (`extra="ignore"`, `kind: Literal[...]`, defaults where legal) and a `SPEC_EXAMPLE` class constant showing a valid spec
- [x] 4.2 Implement `InvalidFilterSpecError.from_validation(kind, exc, fmt, example)` in `backend/app/search/filter.py`: single formatter converting a pydantic `ValidationError` into one message listing the field problems, the expected format, and the concrete example spec
- [x] 4.3 Update `registry.from_spec` to validate specs with the filter's pydantic model (`model_validate`) and raise `InvalidFilterSpecError`; replace any hand-written field checks in filter classes
- [x] 4.4 Update `orchestrator.add_filter` to catch `InvalidFilterSpecError` beside `UnknownFilterKindError` and surface HTTP 422 with the structured message
- [x] 4.5 Add tests: CLIP spec missing required text query returns 422 whose message lists each problem, the expected format, and an example; spec with valid fields plus unknown extras is accepted with extras ignored

## 5. Finalize returns URIs (BREAKING)

- [x] 5.1 Update both finalize paths of `CandidateQuery.finalize` (RRF and no-rank-filters) to `.join(Image, Image.id == <pool>.c.id)` and select `Image.uri`, returning `(id, uri, score)` triples; keep the join inside the final top-K statement per ADR-0002 (no earlier materialization, HNSW push-down untouched)
- [x] 5.2 Change `SearchHit` in `backend/app/search/schemas.py` to `{id, uri, score}` and update hit mapping in `backend/app/search/routes.py`
- [x] 5.3 Update existing search tests asserting finalize response shape to expect `uri` alongside `id` and `score`

## 6. Verification

- [x] 6.1 Run the full suite with `docker compose up -d && make test` and fix regressions
- [x] 6.2 Run `openspec validate search-api-hardening-and-cleanup --type change --strict` before archive
