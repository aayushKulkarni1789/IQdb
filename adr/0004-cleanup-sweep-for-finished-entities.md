# Cleanup Sweep for finished entities

## Status

Accepted

## Date

2026-08-23

## Context and Problem Statement

Finalized `SearchSession` rows and terminal `UploadJob` rows accumulate forever in Postgres. We need recurring deletion of finished entities, but Postgres has no TTL indexes, and the team does not want a new service, scheduler dependency, or DB extension. Whatever mechanism we choose becomes the long-term pattern for entity lifecycle cleanup (including future file deletion under `UPLOAD_ROOT`), so durability semantics must be settled now.

## Considered Options

- APScheduler-based service: dedicated scheduler dependency running sweeps; durable schedules but a second place to look for behavior and another dependency to operate.
- pg_cron inside the Postgres container: SQL-scheduled deletes; couples application lifecycle rules to the database image and complicates local dev.
- In-process asyncio sweep: a task started by the FastAPI lifespan runs a directly callable pass function on a fixed interval (`SWEEP_INTERVAL_MINUTES`, default 24h), unconditionally deleting finalized sessions and terminal jobs (COMPLETED/DISCARD). Schedule is derived in memory (`last_pass + interval`) and never persisted; each pass survives DB outages via try/except.

## Decision Outcome

Chosen option: "In-process asyncio sweep", because sweeps are idempotent convergent deletes - missed or duplicated passes cost nothing - so scheduler infrastructure buys no correctness, only operational surface. First pass fires shortly after boot so restarts catch up immediately. The pass function is callable directly, keeping tests deterministic without timer waits.

### Consequences

- Good, because no new dependency, service, or DB extension is needed; cleanup lives with the application that owns the data.
- Good, because crash/reboot recovery is automatic and stateless; there is no persisted schedule to corrupt or drift.
- Bad, because cleanup lags with backend uptime: if the backend stays down past an interval, finished rows accumulate until it returns.
- Bad, because multi-worker deployments duplicate sweep work (harmless for idempotent DB deletes, but future disk deletion must resolve concurrent directory-deletion races before enabling).
- Follow-up: enabling `UPLOAD_ROOT/<job_id>/` deletion requires its own decision on multi-worker coordination.
