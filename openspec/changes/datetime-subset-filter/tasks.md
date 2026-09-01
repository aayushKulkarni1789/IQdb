## 1. EXIF Extraction and Model Changes

- [ ] 1.1 Modify `extract_capture_time()` in `backend/app/search/exif.py` to return naive datetime (drop timezone offset)
- [ ] 1.2 Update `Image.capture_time` in `backend/app/models.py` from `DateTime(timezone=True)` to `DateTime(timezone=False)`
- [ ] 1.3 Create Alembic migration to alter `capture_time` column from `TIMESTAMPTZ` to `TIMESTAMP` (with downgrade path)
- [ ] 1.4 Add B-tree index on `capture_time` via Alembic migration (`CREATE INDEX CONCURRENTLY`)

## 2. DatetimeFilterSpec Validation

- [ ] 2.1 Define `DayOfWeek` enum in `backend/app/search/filters/datetime.py` (MONDAY=1 through SUNDAY=0 mapping)
- [ ] 2.2 Implement `DatetimeFilterSpec` pydantic model with optional `date_lower`/`date_upper` (`datetime.date`), `time_lower`/`time_upper` (`datetime.time`), `days_included` (`list[DayOfWeek]`)
- [ ] 2.3 Add pydantic `model_validator` to reject inverted ranges (`date_lower > date_upper`, `time_lower > time_upper`) with ValueError
- [ ] 2.4 Update `SPEC_FORMAT` and `SPEC_EXAMPLE` class variables on `DatetimeFilterSpec`

## 3. DatetimeFilter SQL Predicate Generation

- [ ] 3.1 Implement `DatetimeFilter.build_predicate()` generating SQL conjunction: `DATE(capture_time) >= :date_lower`, `DATE(capture_time) <= :date_upper`, `TIME(capture_time) >= :time_lower`, `TIME(capture_time) <= :time_upper`, `EXTRACT(DOW FROM capture_time) IN (...)`
- [ ] 3.2 Set `DatetimeFilter.is_live = True` and update `from_spec()` to use the new `DatetimeFilterSpec`
- [ ] 3.3 Update `list_filters()` or registry to advertise `DatetimeFilter` as live

## 4. Tests

- [ ] 4.1 Write unit tests for `DatetimeFilterSpec` validation: valid spec, inverted date range rejection, inverted time range rejection, standalone days_included
- [ ] 4.2 Write unit tests for `DatetimeFilter.build_predicate()`: date-only, time-only, day-of-week-only, mixed fields, NULL capture_time exclusion
- [ ] 4.3 Write integration test: apply datetime filter to session, verify candidate count, finalize and verify results
- [ ] 4.4 Write integration test: multiple datetime filters compose with OR (same-kind union)

## 5. Verification

- [ ] 5.1 Run `openspec validate datetime-subset-filter --type change --strict` to verify artifact coherence
- [ ] 5.2 Run `make test` to verify all tests pass
