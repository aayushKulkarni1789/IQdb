# Proposal: search-api-hardening-and-cleanup

## Why

Five operational and API-stability gaps compound into real operator and client pain:

- **Ingestion opacity**: upload/embedding jobs end silently. Operators cannot tell whether metadata extraction (file size, dimensions, capture time, GPS) is healthy or quietly degrading — problems only surface later as missing query facets.
- **Unbounded growth**: finalized search sessions and terminal upload jobs (completed *and* discarded) are never deleted, so Postgres accumulates dead rows forever and job directories linger under `UPLOAD_ROOT`.
- **Hostile error surface**: a filter spec with the right `kind` but wrong shape crashes with a raw `KeyError` → 500. Agent clients get no recovery signal (what went wrong and how should a spec look like instead).
- **Open-string filter kinds**: unknown kinds are already rejected at add-time (422 via `UnknownFilterKindError`), but the contract is only enforced by runtime error flow — there is no schema-level safety, no documented enum in OpenAPI, and nothing stops internal code from persisting a typo'd kind.
- **ID-only finalize**: finalize returns bare image IDs, forcing every client into follow-up lookups to resolve URIs and coupling callers to internal ID semantics.

Fixing these together is one cohesive hardening pass across observability, lifecycle hygiene, and API contract stability; splitting them would touch the same modules repeatedly.

## What Changes

- **Ingestion summary log**: `process_upload_embeddings` emits one INFO line at job completion — total files, opened_ok, written_to_db, per-field metadata counts (`file_size`, `dimensions`, `capture_time`, `gps`; grouped fields count as extracted only when all constituent columns persisted non-NULL), elapsed seconds, status=completed. A shorter partial summary with status=failed is logged when the job crashes mid-run.
- **Cleanup sweep** (deliberately *not* called TTL — Postgres has no TTL indexes): an in-process asyncio task started in a new FastAPI lifespan handler (created from scratch; none exists today) runs a first pass shortly after boot and repeats every `SWEEP_INTERVAL_MINUTES`. Each pass unconditionally deletes finalized `SearchSession` rows and terminal `UploadJob` rows (status COMPLETED or DISCARD) — no retention-age check; finalize/completion is treated as terminal. Each pass is implemented as a directly callable function so tests can invoke it without waiting on the timer; the loop itself survives DB outages via per-pass try/except (WARNING logged, retried next tick). The schedule is derived in-process and never persisted — idempotent deletes make missed sweeps cost-free. Physical deletion of `UPLOAD_ROOT/<job_id>/` is coded but commented out with an explanatory note (future work: concurrent workers could race on directory deletion, so disk cleanup needs that discussion first); DB rows only for now.
- **`FilterKind` StrEnum**: CLIP/DATETIME/GEO/FACE defined in `app/search/filter.py`; the filter registry keys off the enum. `registry.from_spec` converts the incoming spec string to `FilterKind` before lookup (unknown values raise the existing 422 path — no silent `KeyError`). Persisted JSONB specs remain string-compatible (StrEnum values round-trip as plain strings). `FilterAddRequest.kind` becomes strictly typed, so pydantic auto-rejects unknown kinds with 422 at request validation and documents the valid set in OpenAPI.
- **Actionable spec-validation errors**: every filter class declares a pydantic spec model (`extra="ignore"`) and a `SPEC_EXAMPLE` constant. Validation failures funnel through `InvalidFilterSpecError.from_validation(kind, exc, fmt, example)` in `app/search/filter.py` — a single formatter producing the problem list, expected format, and a concrete example — surfaced as HTTP 422 from `orchestrator.add_filter`, replacing today's KeyError/500 behavior.
- **Finalize returns URIs** — **BREAKING** (additive field; breaks strict-schema/OpenAPI-generated clients only): `CandidateQuery.finalize` returns `(id, uri, score)` triples via a PK join into `image` in both the RRF and no-rank-filters paths; `SearchHit` becomes `{id, uri, score}`. Handled within v1 — no versioned endpoint, since existing `id`/`score` semantics are unchanged. No new database indexes are required (`Image.id` is PK-indexed; `CLIP_Embedding.image_id` is uniquely constrained).

## Capabilities

### New Capabilities
- **cleanup-sweep**: periodic in-process background deletion of finished entities — finalized search sessions and terminal (COMPLETED/DISCARD) upload jobs — on a fixed configurable interval, resilient to restarts (schedule derived at runtime, never persisted) and DB outages (failed passes logged as WARNING and retried next tick).
- **ingestion-reporting**: machine-readable end-of-job summary logging for CLIP ingestion, covering volume totals, per-field metadata extraction health, elapsed time, and terminal status — including a distinct failure-path partial summary.

### Modified Capabilities
- **image-search**: strict `FilterKind` validation on filter add (unknown kinds → automatic 422 at request validation), structured actionable spec-error messages (422 with expected format and example, replacing 500s), and finalize hits gaining a `uri` field alongside `id` and `score` (**BREAKING** for strict-schema clients).

## Impact

- **Code**: `backend/app/tasks.py` (summary counters/timing + log lines); new sweep-task module plus a lifespan handler in `backend/app/main.py` (startup starts the task, shutdown cancels it); `backend/app/core/config.py` + `.env.example` (`SWEEP_INTERVAL_MINUTES`, hours-scale default pinned in design); `backend/app/models.py` (no schema change — no migration); `backend/app/search/filter.py` (`FilterKind`, `InvalidFilterSpecError`); `backend/app/search/registry.py` (enum-keyed registry with str→enum conversion); `backend/app/search/filters/*.py` (pydantic spec models, `SPEC_EXAMPLE`); `backend/app/search/orchestrator.py` (catch new error → 422; thread URIs through); `backend/app/search/schemas.py` + `routes.py` (`SearchHit.uri`, hit mapping).
- **APIs**: `POST /api/v1/sessions/{id}/finalize` hits gain `uri` (**BREAKING** for strict clients, additive otherwise); filter-add failures move from 500 to structured 422 bodies; invalid kinds rejected at request validation with 422. Alerting keyed on 500 rates for these endpoints will shift accordingly.
- **Ops/env**: one new env var (`SWEEP_INTERVAL_MINUTES`); background task lives inside the backend container — no new service, no scheduler dependency. Under multi-worker deployment each worker sweeps independently; DB deletes are idempotent, so overlap is wasted work, not corruption (see disk-race caveat above for the deferred file cleanup). Sweep logging: INFO when a pass deletes rows, DEBUG for empty passes, WARNING on DB outage retry. Tests may run sweeps concurrently with fixtures; suites must complete within one interval, and sweep behavior is covered by invoking the pass function directly.
- **Database**: no migrations. Deletes target only rows already flagged finalized or in a terminal job status; there is no age-based retention, so swept sessions/jobs cannot be re-fetched afterward — intended.
- **Specs**: modifies the existing `image-search` spec; introduces new spec directories `specs/cleanup-sweep/` and `specs/ingestion-reporting/` on apply.
