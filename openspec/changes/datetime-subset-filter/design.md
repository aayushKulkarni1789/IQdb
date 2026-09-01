## Context

The image search pipeline uses a two-phase filter model (ADR-0001): **SubsetFilter** emits `WHERE` predicates, **RankFilter** emits rank CTEs fused by RRF (ADR-0003). The candidate set is a lazy SQL `Select` via **CandidateQuery** (ADR-0002) — no image IDs materialize until the final `LIMIT K`.

Today, `DatetimeFilter` is a registered stub with `is_live=False` that rejects all requests with 501. The EXIF extraction pipeline (`exif.py`) already populates `capture_time` during ingestion, storing timezone-aware timestamps (`TIMESTAMPTZ`). The column type must change to `TIMESTAMP` (naive local time) because the filter operates on local date/time fields without timezone semantics.

## Goals / Non-Goals

**Goals:**
- Promote `DatetimeFilter` to a live **SubsetFilter** that generates SQL WHERE clauses over `capture_time`
- Validate filter specs with pydantic: independent optional date/time fields + day-of-week array
- Reject inverted ranges with 422
- Add a B-tree index on `capture_time` for query performance
- Change `capture_time` from `TIMESTAMPTZ` to `TIMESTAMP` (naive local time)

**Non-Goals:**
- Supporting timezone-aware queries or UTC-normalized time ranges
- implementing `GeoFilter` or `FaceFilter` (remain stubs)
- Configurable per-filter RRF weights (ADR-0003 scope)
- Multi-column composite index on `capture_time` + other fields

## Decisions

### D1: Naive local time for `capture_time`

Store `capture_time` as `TIMESTAMP` (no timezone). EXIF extraction returns `datetime` without `tzinfo`. The timezone offset from `OffsetTimeOriginal` is discarded.

**Rationale**: The filter operates on local date/time fields (`date_lower`, `time_lower`, `days_included`) that have no timezone semantics. Storing UTC would require converting local EXIF time to UTC at ingestion and back to local time at query time — unnecessary complexity for a feature that queries "what time of day was this taken?" not "what absolute instant?".

**Alternatives considered**:
- Store as `TIMESTAMPTZ` and convert at query time: rejected — adds conversion complexity and makes `DATE()` / `TIME()` / `EXTRACT(DOW)` ambiguous (which timezone?).
- Store both local and UTC: rejected — schema bloat for no current use case.

### D2: `DatetimeFilterSpec` field types

```python
class DayOfWeek(str, Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"

class DatetimeFilterSpec(BaseModel):
    kind: Literal[FilterKind.DATETIME] = FilterKind.DATETIME
    date_lower: date | None = None
    date_upper: date | None = None
    time_lower: time | None = None
    time_upper: time | None = None
    days_included: list[DayOfWeek] | None = None
```

All five fields are optional and independent — no pair constraints. Pydantic validates types; custom `model_validator` rejects inverted ranges.

**Rationale**: Independent fields compose naturally via AND in SQL. A user can filter by date range only, time range only, day-of-week only, or any combination. Pair constraints would restrict valid use cases without benefit.

### D3: SQL predicate generation

`DatetimeFilter.build_predicate()` produces a conjunction of optional clauses:

```sql
DATE(capture_time) >= :date_lower       -- if date_lower provided
DATE(capture_time) <= :date_upper       -- if date_upper provided
TIME(capture_time) >= :time_lower       -- if time_lower provided
TIME(capture_time) <= :time_upper       -- if time_upper provided
EXTRACT(DOW FROM capture_time) IN (...) -- if days_included provided
```

DOW mapping: `MONDAY=1, TUESDAY=2, ..., SUNDAY=0` (PostgreSQL convention).

**Rationale**: Each field maps to an independent SQL clause. `NULL` capture_time rows are excluded automatically by SQL NULL comparison semantics — no `IS NOT NULL` guard needed.

### D4: `DayOfWeek` enum location

Define `DayOfWeek` in `backend/app/search/filters/datetime.py` alongside `DatetimeFilterSpec`. It is only used by the datetime filter and has no cross-module dependencies.

### D5: Inverted range validation

Pydantic `model_validator` (mode=`after`) checks:
- If both `date_lower` and `date_upper` are set, `date_lower <= date_upper`
- If both `time_lower` and `time_upper` are set, `time_lower <= time_upper`

Raises `ValueError` on violation, caught by the existing `InvalidFilterSpecError` path → 422 with actionable message.

### D6: `SPEC_FORMAT` and `SPEC_EXAMPLE`

```python
SPEC_FORMAT: ClassVar[str] = (
    '{"kind": "datetime", "date_lower": "2024-01-01", "date_upper": "2024-12-31", '
    '"time_lower": "08:00:00", "time_upper": "18:00:00", '
    '"days_included": ["MONDAY", "WEDNESDAY"]}'
)
SPEC_EXAMPLE: ClassVar[dict] = {
    "kind": "datetime",
    "date_lower": "2024-01-01",
    "date_upper": "2024-12-31",
    "time_lower": "08:00:00",
    "time_upper": "18:00:00",
    "days_included": ["MONDAY", "WEDNESDAY"],
}
```

### D7: B-tree index on `capture_time`

Add a standard B-tree index via Alembic migration. Use `CREATE INDEX CONCURRENTLY` if the table is large to avoid locking.

**Rationale**: The datetime filter applies `DATE()`, `TIME()`, and `EXTRACT()` functions to `capture_time`. A B-tree index supports range scans on the raw column; function-based queries benefit from the index when PostgreSQL can fold `DATE(capture_time)` comparisons.

## Risks / Trade-offs

- **[Timezone ambiguity]** → Images from different timezones at the same local time are indistinguishable. This is accepted: the filter queries local time semantics, not absolute instants. Mitigated by documenting the behavior.
- **[Existing data conversion]** → `ALTER COLUMN TYPE` from `TIMESTAMPTZ` to `TIMESTAMP` drops timezone offsets from existing rows. Existing timezone-aware values will have their offset stripped. This is acceptable because no existing datetime filter specs exist (it was a stub).
- **[Index creation lock]** → `CREATE INDEX` on a large table can lock writes. Mitigated by using `CREATE INDEX CONCURRENTLY` in the migration.
- **[NULL capture_time]** → Images without EXIF datetime are excluded from all datetime predicates. This is correct SQL behavior and matches user expectations.

## Migration Plan

1. **Alembic migration (upgrade)**:
   - `ALTER TABLE image ALTER COLUMN capture_time TYPE TIMESTAMP` — drops timezone
   - `CREATE INDEX CONCURRENTLY ix_image_capture_time ON image (capture_time)` — B-tree index
2. **Alembic migration (downgrade)**:
   - `DROP INDEX ix_image_capture_time`
   - `ALTER TABLE image ALTER COLUMN capture_time TYPE TIMESTAMP WITH TIME ZONE USING capture_time AT TIME ZONE 'UTC'`
3. **EXIF extraction change**: `extract_capture_time()` returns naive `datetime` (no `tzinfo`).
4. **Model change**: `Image.capture_time` field changes from `DateTime(timezone=True)` to `DateTime(timezone=False)`.

## Open Questions

_(none — all design decisions resolved)_
