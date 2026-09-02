# Datetime Filter (kind: `datetime`) — Subset Filter

## What it does
Subset filter that narrows candidates by capture time extracted from EXIF `DateTimeOriginal` (stored as naive local time per ADR-0005). All active predicates are `AND`ed; multiple `datetime` filters of the same kind are `OR`ed, then cross-kind `AND`ed with other subset kinds. An empty spec matches all images (`literal(True)`).

## How to use
Call the `add_datetime_filter` tool with any subset of the optional fields. Validated by `DatetimeFilterSpec` (`extra="ignore"`). Lower bounds must be `<=` upper bounds.

**Spec format:** `{"kind": "datetime", "date_lower": "2024-01-01", "date_upper": "2024-12-31", "time_lower": "08:00:00", "time_upper": "18:00:00", "days_included": ["MONDAY", "WEDNESDAY"]}`

**Example:** `{"kind": "datetime", "date_lower": "2024-01-01", "date_upper": "2024-12-31", "time_lower": "08:00:00", "time_upper": "18:00:00", "days_included": ["MONDAY", "WEDNESDAY"]}`

**Fields (all optional):**
- `date_lower` / `date_upper` (date, ISO `YYYY-MM-DD`): inclusive calendar-date bounds on `capture_time`.
- `time_lower` / `time_upper` (time, `HH:MM:SS`): inclusive wall-clock time bounds.
- `days_included` (list[DayOfWeek]): `["MONDAY".."SUNDAY"]`; maps to Postgres `EXTRACT(DOW)` (MONDAY=1..SATURDAY=6, SUNDAY=0). Matches if `capture_time` falls on any listed day.

## When to use
Use when the user mentions dates, date ranges, times of day, or days of week (e.g., "photos from last summer", "evening shots", "weekend trips"). Combine with rank filters (e.g., `clip`) for time-bounded semantic search. Omit fields you do not need.

## Note
- If not provided, time upper limit is JUST BEFORE MIDNIGHT, and time lower limit is MIDNIGHT
- If the requested time range spans over midnight, then you would need to use two filters to cover the range
