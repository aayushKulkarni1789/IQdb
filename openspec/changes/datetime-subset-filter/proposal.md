## Why

The datetime filter is currently a registered stub that rejects all requests with 501. Users need to narrow image searches by capture date/time (e.g. "show me photos from last summer", "only images taken in the evening"). The EXIF extraction pipeline already populates `capture_time` during ingestion, so the data is ready — only the filter logic and a timezone handling fix are missing.

## What Changes

- **BREAKING**: Change `capture_time` column from `TIMESTAMPTZ` to `TIMESTAMP` (naive local time). EXIF extraction drops timezone offset, storing local time directly. Existing timezone-aware values will have their offset stripped by PostgreSQL's `ALTER COLUMN TYPE` conversion.
- **BREAKING**: Alembic migration to alter column type and add B-tree index. Downgrade reverts the column type and drops the index.
- Implement `DatetimeFilter` as a live `SubsetFilter` with `build_predicate()` generating SQL WHERE clauses.
- Add `DatetimeFilterSpec` with pydantic validation: `date_lower`/`date_upper` (`datetime.date`), `time_lower`/`time_upper` (`datetime.time`), all optional and independent (no pair constraints). `days_included` (array of `DayOfWeek` enum: `MONDAY`, `TUESDAY`, etc., all caps) — works standalone.
- Reject inverted ranges (`date_lower > date_upper`, `time_lower > time_upper`) with HTTP 422.
- Add B-tree index on `capture_time` for query performance. Use non-blocking creation if available.

## Capabilities

### New Capabilities

_(none — this modifies an existing capability)_

### Modified Capabilities

- `image-search`: Two requirements change:
  1. "Datetime, geo, and face filters are registered stubs" — `DatetimeFilter` becomes a live subset filter with full SQL predicate generation, pydantic validation, day-of-week filtering, inverted-range rejection, and index-backed queries. Geo and face filters remain stubs.
  2. "EXIF metadata columns are populated during ingestion" — `capture_time` column type changes from TIMESTAMPTZ to TIMESTAMP. EXIF extraction returns naive datetime. ImagePublic returns naive datetime (no timezone in ISO-8601 output).

## Impact

- `backend/app/search/filters/datetime.py` — full implementation of `DatetimeFilter` and `DatetimeFilterSpec`
- `backend/app/search/exif.py` — `extract_capture_time()` returns naive datetime (drops timezone offset)
- `backend/app/models.py` — `capture_time` field changes from `DateTime(timezone=True)` to `DateTime(timezone=False)`
- `backend/app/alembic/versions/` — new migration: ALTER COLUMN type + CREATE INDEX (with downgrade)
- `backend/tests/` — tests for valid range query, time-only, date-only, day-of-week only, mixed fields, inverted range rejection (422), NULL capture_time exclusion
- `openspec/specs/image-search/spec.md` — updated requirements for live datetime filter and naive datetime column type
