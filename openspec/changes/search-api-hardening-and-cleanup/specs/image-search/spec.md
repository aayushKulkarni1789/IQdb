# image-search Delta

## ADDED Requirements

### Requirement: Filter kinds are strictly validated against an enumerated set
The set of filter kinds SHALL be a closed enumeration (CLIP, DATETIME, GEO, FACE) exposed as **FilterKind** and enforced by strict typing on the filter-add request schema, so unknown kinds are rejected at request validation with HTTP 422 naming the valid values. The registry SHALL look up filter classes by **FilterKind**, converting the persisted spec's kind string to the enum before lookup; unknown strings surface as 422, never a silent lookup miss. Persisted specs remain string-compatible.

Feature: image-search
Rule: only enumerated kinds enter the system, checked at the request boundary

#### Scenario: An unknown filter kind is rejected at request validation
- **GIVEN** an open search session
- **WHEN** the agent calls `POST /sessions/{id}/filters` with an unknown kind such as `"clipp"`
- **THEN** the API returns `422` with validation detail identifying the invalid kind
- **AND** the detail documents the valid values (CLIP, DATETIME, GEO, FACE)
- **AND** no spec is appended to the session

#### Scenario: Persisted specs round-trip through the enum unchanged
- **GIVEN** a session with previously applied filters stored in its specs log
- **WHEN** new filters are added after kinds become strictly typed
- **THEN** existing persisted specs remain valid and finalize behaves identically
- **AND** no data migration is required

### Requirement: Malformed filter specs return actionable 422 errors
A filter spec with a valid **FilterKind** but missing or mistyped fields SHALL be rejected with HTTP 422 carrying a single message that lists the validation problems, describes the expected format, and includes a concrete example of a valid spec — instead of an unhandled server error. Unknown extra fields in a spec SHALL be ignored.

Feature: image-search
Rule: every spec rejection tells the agent what was wrong, what the format is, and shows a valid example

#### Scenario: A valid kind with malformed fields returns a structured error
- **GIVEN** an open search session
- **WHEN** the agent applies a CLIP filter whose spec omits the required text query
- **THEN** the API returns `422`
- **AND** the response message lists each field problem, the expected format for the CLIP spec, and a concrete example spec
- **AND** no spec is appended to the session

#### Scenario: Unknown extra fields in a spec are ignored
- **GIVEN** an open search session
- **WHEN** the agent applies a CLIP filter whose spec contains the required text query plus unrecognized extra fields
- **THEN** the filter is accepted with the extra fields ignored
- **AND** the spec appends normally

## MODIFIED Requirements

### Requirement: Search session lifecycle
An agent SHALL create a search session, apply filters in any order, then finalize to obtain Top-K image hits. The session MUST be terminal: once finalized it MUST NOT accept more filters or be finalized again.

Feature: image-search
Rule: a session accumulates an ordered filter spec log and is finalized exactly once

#### Scenario: Create a new search session
- **GIVEN** a request to start a new image search
- **WHEN** the agent calls `POST /sessions`
- **THEN** a new `SearchSession` row is created with an empty specs log, `finalized = false`, and a `created_at` timestamp
- **AND** the response returns the new session `id`

#### Scenario: Apply filters in any order before finalize
- **GIVEN** an open (not finalized) search session
- **WHEN** the agent calls `POST /sessions/{id}/filters` one or more times in any order
- **THEN** each filter spec is appended to the session's ordered JSONB specs log
- **AND** the response returns the running `candidate_count` (the phase-1 subset pool size)

#### Scenario: Finalize a session and obtain Top-K hits with URIs
- **GIVEN** an open search session with zero or more applied filters
- **WHEN** the agent calls `POST /sessions/{id}/finalize`
- **THEN** the session's `finalized` flag is set to true
- **AND** the response returns `number_of_images_in_output` Top-K hits, each carrying the image's `id`, its `uri`, and its `score`

#### Scenario: A finalized session rejects further operations
- **GIVEN** a search session that has already been finalized
- **WHEN** the agent calls `POST /sessions/{id}/filters` or `POST /sessions/{id}/finalize` again
- **THEN** the API returns `409 Conflict`
