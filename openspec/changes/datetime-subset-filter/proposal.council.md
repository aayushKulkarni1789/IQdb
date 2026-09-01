# Council Notes: proposal.md

## Author Summary
Draft established the core proposal: promote DatetimeFilter from stub to live SubsetFilter, change capture_time from TIMESTAMPTZ to TIMESTAMP, add pydantic-validated DatetimeFilterSpec with independent optional fields, reject inverted ranges, add B-tree index.

## Reviewer Challenges
- Missing migration downgrade path — existing migrations have explicit downgrade logic
- DayOfWeek enum location unspecified — needs a defined module
- Existing spec scenarios reference "timezone offset" and "ISO-8601 with timezone" — must be updated for naive datetime
- Existing data conversion semantics not documented (PostgreSQL strips offset on ALTER TYPE)
- Pydantic field types unspecified (datetime.date / datetime.time vs strings)
- Explicit standalone semantics for days_included not surfaced in "What Changes"
- SPEC_FORMAT/SPEC_EXAMPLE on the filter class not mentioned
- Index creation on large tables could lock — consider non-blocking strategy

## Resolutions
- Accepted: Added downgrade path note, specified naive datetime conversion behavior, added non-blocking index note
- Accepted: Specified pydantic types as datetime.date and datetime.time
- Accepted: Called out both modified requirements (stub filter + EXIF column type) in Capabilities
- Accepted: Added days_included standalone semantics explicitly
- Rejected: DayOfWeek enum location left for design phase (not a proposal-level concern)
- Rejected: Test scenario enumeration kept brief (design/tasks will detail)

## Remaining Risks
- Timezone ambiguity with naive datetime: images from different timezones at same local time are indistinguishable — user accepted this tradeoff in grill
- Day-of-week computed from stored local time, not UTC — user confirmed this is intended
- No existing sessions have datetime specs (was a stub), so migration ordering is safe
