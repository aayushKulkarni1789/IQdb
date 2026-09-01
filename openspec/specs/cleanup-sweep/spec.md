# cleanup-sweep Specification

## Purpose
Periodic in-process background deletion of finished entities — finalized search sessions and terminal upload jobs — so finished rows do not accumulate forever. The schedule is derived at runtime and never persisted; failed passes are logged and retried on the next tick.

## Requirements

### Requirement: Finalized search sessions are deleted automatically
The system SHALL periodically delete every finalized **SearchSession** as part of a **Cleanup Sweep** pass. Finalize is treated as terminal: once swept, a session cannot be re-fetched or resumed.

Feature: cleanup-sweep
Rule: finalize is terminal, and terminal sessions are garbage-collected on the next sweep pass

#### Scenario: A sweep pass deletes finalized search sessions
- **GIVEN** one finalized search session and one open search session exist
- **WHEN** a **Cleanup Sweep** pass runs
- **THEN** the finalized session is deleted and can no longer be fetched
- **AND** the deletion is reported at INFO level

#### Scenario: Open search sessions survive the sweep
- **GIVEN** a search session that has not been finalized
- **WHEN** a **Cleanup Sweep** pass runs
- **THEN** the session still exists
- **AND** it can still accept filters and be finalized normally

### Requirement: Terminal upload jobs are deleted automatically
The system SHALL periodically delete every **Terminal UploadJob** (status COMPLETED or DISCARD) as part of a **Cleanup Sweep** pass. Upload jobs still in progress MUST NOT be deleted.

Feature: cleanup-sweep
Rule: both terminal job states are eligible; only terminal states are eligible

#### Scenario: A sweep pass deletes completed upload jobs
- **GIVEN** an upload job whose processing completed successfully
- **WHEN** a **Cleanup Sweep** pass runs
- **THEN** the job row is deleted

#### Scenario: A sweep pass deletes discarded upload jobs
- **GIVEN** an upload job that ended in the DISCARD state
- **WHEN** a **Cleanup Sweep** pass runs
- **THEN** the job row is deleted

#### Scenario: Active upload jobs survive the sweep
- **GIVEN** an upload job that is pending or currently processing
- **WHEN** a **Cleanup Sweep** pass runs
- **THEN** the job row is retained
- **AND** its processing is unaffected

### Requirement: The sweep runs on a fixed interval derived at runtime
A **Cleanup Sweep** loop SHALL run inside the backend process, perform its first pass shortly after startup, and repeat every `SWEEP_INTERVAL_MINUTES`. The schedule SHALL be computed in memory from the last pass time and never persisted; no age threshold applies to what a pass deletes.

Feature: cleanup-sweep
Rule: re-running a pass converges to the same state, so a missed or repeated window costs nothing

#### Scenario: The first pass after boot catches up on pre-existing finished rows
- **GIVEN** finalized search sessions and terminal upload jobs exist before the backend starts
- **WHEN** the backend finishes starting up
- **THEN** a first sweep pass runs shortly after boot
- **AND** the pre-existing finished rows are deleted

#### Scenario: Passes repeat on the configured interval without persistence
- **GIVEN** the backend runs with `SWEEP_INTERVAL_MINUTES` configured
- **WHEN** successive intervals elapse
- **THEN** a sweep pass fires at each interval boundary
- **AND** restarting the backend recomputes the schedule in memory without any stored schedule state

### Requirement: The sweep survives database unavailability
Each **Cleanup Sweep** pass SHALL tolerate database failures: a failing pass logs a WARNING and the loop continues, retrying on the next tick.

Feature: cleanup-sweep
Rule: an outage delays sweeping but never crashes the backend

#### Scenario: A failed pass is logged and retried on the next tick
- **GIVEN** the database is unavailable when a sweep pass fires
- **WHEN** the pass attempts its deletions
- **THEN** the failure is logged at WARNING level
- **AND** the backend keeps running and the loop stays alive
- **AND** the next pass after the database recovers deletes all accumulated finished rows
