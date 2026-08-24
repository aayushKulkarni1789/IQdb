# Design: search-api-hardening-and-cleanup

## Context

The backend (`backend/app/`) is a FastAPI service over Postgres/pgvector. Ingestion runs as a synchronous task (`tasks.process_upload_embeddings`) that batches images through CLIP and writes `Image` + `CLIP_Embedding` rows. Search is the lazy **CandidateQuery** push-down described in ADR 0002, fused by **RRF** (ADR 0003) over filters classified by the subset/rank taxonomy (ADR 0001). Today:

- The ingestion task logs per-batch progress but nothing summarizing metadata extraction health.
- `SearchSession` rows (once finalized) and `UploadJob` rows (once terminal) are never deleted.
- `Filter.kind` is an open string; unknown kinds are rejected at add-time (422 via `UnknownFilterKindError`), but there is no schema-level contract, and a spec with a valid kind but missing/mistyped fields raises raw `KeyError` → HTTP 500.
- `CandidateQuery.finalize` returns `(id, score)` pairs of bare image IDs.
- `main.py` has no lifespan handler; nothing runs in the background.

Constraints: Postgres has no TTL indexes; the team wants no new services or scheduler dependencies; tests share one backend container and must stay deterministic; all three ADRs above remain in force and this design must not violate them.

## Goals / Non-Goals

**Goals:**
- One INFO summary line per ingestion job (success or failure path) with volume, per-field metadata health, elapsed time, terminal status.
- Automatic deletion of finished entities by an in-process cleanup sweep on a fixed interval.
- Compile-time/schema-level safety for filter kinds via a `FilterKind` StrEnum.
- Agent-actionable 422 errors for malformed filter specs (expected format + example).
- Finalize hits carry `uri` alongside `id` without breaking the lazy SQL model.

**Non-Goals:**
- Deleting files under `UPLOAD_ROOT` (code written but commented out; needs a concurrency decision first).
- Age-based retention windows or per-entity TTL configuration.
- Implementing datetime/geo/face filter logic (still stubs).
- Versioning the search API (v2 routes).
- Any database schema migration.

## Decisions

### D1 — Cleanup sweep: in-process asyncio loop (not APScheduler, not pg_cron)
A single asyncio task started from a new FastAPI lifespan handler; shutdown cancels it. Chosen because sweeps are idempotent deletes — durability infrastructure (scheduler service, cron extension) buys nothing for stateless work that converges on retry. Alternatives: APScheduler adds a dependency and a second place to look for behavior; pg_cron puts application lifecycle inside the DB container and complicates local dev.

### D2 — Derived schedule, unconditional deletion
Each pass deletes *every* finalized `SearchSession` and every terminal `UploadJob` (status `COMPLETED` or `DISCARD`). No age threshold, no persisted schedule: `next_pass = last_pass + interval`, computed in memory. A missed window costs nothing because re-running converges to the same DB state. First pass fires shortly after boot so a restarted backend immediately catches up.

### D3 — Sweep pass is a plain callable
The delete logic lives in a standalone function (new module, e.g. `app/core/cleanup.py`) taking a `Session`; the asyncio loop just calls it on the interval. Tests invoke the function directly instead of waiting on timers, keeping suites deterministic even though the real loop also runs during them. Logging per pass: INFO when rows were deleted, DEBUG when empty, WARNING on DB outage (loop survives via try/except).

### D4 — Interval default: `SWEEP_INTERVAL_MINUTES = 1440`
One env var, defaulting to 24h — hours-scale so test windows are never hit in practice. Configured via existing pydantic-settings `Settings`.

### D5 — `FilterKind` StrEnum keyed registry
`class FilterKind(StrEnum)` in `app/search/filter.py` with CLIP/DATETIME/GEO/FACE; each filter class sets `kind: ClassVar[FilterKind]`. `registry.from_spec` converts the incoming JSONB string with `FilterKind(value)` before lookup — unknown values raise the existing 422-mapped error, never a silent `KeyError`. Persisted specs keep storing plain strings (StrEnum round-trips), so no data migration. `FilterAddRequest.kind: FilterKind` moves rejection of bad kinds into request validation (auto-422 documenting valid values in OpenAPI).

### D6 — Pydantic spec models + single error formatter
Each filter declares a pydantic model for its spec (`extra="ignore"`, `kind: Literal[...]`, defaults where legal) and a `SPEC_EXAMPLE` class constant. `from_spec` does `model_validate` and converts `ValidationError` via `InvalidFilterSpecError.from_validation(kind, exc, fmt=..., example=cls.SPEC_EXAMPLE)` — defined once in `filter.py` next to `FilterKind`. Message template: problem list, expected format, concrete example. `orchestrator.add_filter` catches it beside `UnknownFilterKindError` → HTTP 422. This replaces hand-written field checks and gives agents a self-service recovery path.

### D7 — Finalize joins to `image` for URIs
Both finalize paths append `.join(Image, Image.id == <pool>.c.id)` and select `Image.uri` alongside id/score; return type becomes `list[tuple[int, str, float | None]]`. This stays coherent with ADR 0002: the join lives in the final top-K statement, so nothing materializes earlier and HNSW push-down inside rank CTEs is untouched. PK index makes the join O(log n) per returned row (~top_k); no new indexes. `SearchHit` becomes `{id, uri, score}`; additive within v1.

### D8 — Ingestion summary counters
Wrap the task body in `time.monotonic()`; count per batch: `total` (files seen), `opened_ok`, `written_to_db` (rows actually committed), and non-NULL persistence counts for `file_size`, `dimensions` (width AND height), `capture_time`, `gps` (latitude AND longitude). Success line logs all counts + elapsed + `status=completed`; the exception handler logs counts-so-far + `status=failed` before discarding the job.

## Risks / Trade-offs

- [Finalized sessions vanish under active clients] -> Interval is hours-scale and documented; if replay is ever needed, revisit with a retention window rather than silently extending scope.
- [Multi-worker deployments run duplicate sweeps] -> Idempotent deletes make overlap wasted work only; noted for ops.
- [Commented-out disk deletion could be enabled naively] -> Comment block names the multi-worker directory-race concern that must be resolved first.
- [Strict `FilterAddRequest.kind` changes error shape for bad kinds] -> Still 422; body moves from custom detail string to pydantic validation detail listing valid values.
- [Sweeper running in tests could surprise long-running suites] -> Pass function is separately invocable; suites shorter than the interval are unaffected.
- [500→422 shift invalidates 500-rate alerting on filter add] -> Called out in proposal Impact; dashboards updated at apply time.

## Migration Plan

1. Deploy backend; lifespan starts sweeper automatically; first pass deletes any pre-existing finished rows (safe catch-up).
2. No DB migration, no backfill, no env var required to boot (default applies). Add `SWEEP_INTERVAL_MINUTES=1440` to `.env` explicitly when tuning.
3. Rollback = redeploy previous image; worst case leaves finished rows accumulating again (the status quo).

## Open Questions

- None blocking. Future work flagged for its own change: enabling `UPLOAD_ROOT` file deletion (needs multi-worker coordination decision).
