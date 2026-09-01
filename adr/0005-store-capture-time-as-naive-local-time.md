# Store capture_time as naive local time (TIMESTAMP)

## Context and Problem Statement

The EXIF extraction pipeline populates `capture_time` during ingestion. The column was originally `TIMESTAMPTZ` (timezone-aware), but the datetime filter operates on local date/time fields (`date_lower`, `time_lower`, `days_included`) that have no timezone semantics. We need to decide how to represent `capture_time` so that datetime queries are unambiguous.

## Considered Options

- Store as `TIMESTAMPTZ` and convert at query time — requires converting local EXIF time to UTC at ingestion and back to local time at query time; makes `DATE()` / `TIME()` / `EXTRACT(DOW)` ambiguous.
- Store as `TIMESTAMP` (naive local time) — EXIF extraction discards timezone offset; queries operate directly on local time.
- Store both local and UTC — schema bloat for no current use case.

## Decision Outcome

Chosen option: "Store as `TIMESTAMP` (naive local time)", because the filter queries local time semantics ("what time of day was this taken?"), not absolute instants. Discarding the timezone offset at ingestion eliminates conversion complexity and makes `DATE()`, `TIME()`, and `EXTRACT(DOW)` unambiguous.

### Consequences

- Good, because datetime queries are straightforward — no timezone conversion logic.
- Good, because `DATE()`, `TIME()`, `EXTRACT(DOW)` operate on the stored value directly.
- Bad, because images from different timezones at the same local time are indistinguishable.
- Bad, because existing `TIMESTAMPTZ` values have their offset stripped during migration (acceptable — no datetime filter specs existed when the column was timezone-aware).
