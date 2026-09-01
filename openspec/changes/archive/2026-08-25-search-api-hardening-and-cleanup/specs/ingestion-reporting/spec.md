# ingestion-reporting Specification

## Purpose
Machine-readable end-of-job summary logging for CLIP ingestion: volume totals, per-field metadata extraction health, elapsed time, and terminal status — for both the success and failure paths.

## Requirements

## ADDED Requirements

### Requirement: Completed ingestion jobs emit a summary log with volume, metadata health, and timing
When an ingestion job completes successfully, the system SHALL emit a single **Ingestion Summary Log** line at INFO level reporting: total files seen (`total`), files opened successfully (`opened_ok`), images written to the database (`written_to_db`), per-field metadata extraction counts for `file_size`, `dimensions`, `capture_time`, and `gps`, elapsed time, and `status=completed`.

Feature: ingestion-reporting
Rule: one summary line per job makes metadata-extraction health observable without per-image noise

#### Scenario: A successful job logs a full summary
- **GIVEN** an uploaded batch of images with varying EXIF completeness
- **WHEN** the ingestion job finishes processing all files successfully
- **THEN** exactly one INFO summary line is emitted for the job
- **AND** it reports `total`, `opened_ok`, `written_to_db`, the `file_size` / `dimensions` / `capture_time` / `gps` counts, elapsed time, and `status=completed`

#### Scenario: Grouped metadata fields count only fully extracted values
- **GIVEN** an uploaded image whose width was extracted but whose height was missing
- **WHEN** the ingestion job finishes
- **THEN** that image is excluded from the `dimensions` count (both width AND height must be persisted)
- **AND** an image is counted under `gps` only when both latitude and longitude are persisted non-NULL

#### Scenario: Unreadable files are counted in totals but excluded from written counts
- **GIVEN** an uploaded batch containing a file the pipeline cannot open alongside valid images
- **WHEN** the ingestion job finishes
- **THEN** `total` includes the unreadable file while `opened_ok` and `written_to_db` exclude it

### Requirement: Failed ingestion jobs emit a partial summary before termination
When an ingestion job crashes mid-run, the system SHALL emit a partial **Ingestion Summary Log** line with the counters accumulated so far and `status=failed`.

Feature: ingestion-reporting
Rule: even failed jobs leave an observable record of how far they got

#### Scenario: A crash mid-run logs status=failed with counts so far
- **GIVEN** an ingestion job is partway through its batches when an unrecoverable error occurs
- **WHEN** the job aborts
- **THEN** a partial summary line is emitted with the counters accumulated up to the failure and `status=failed`
- **AND** the job is then marked discarded as before
