# image-search Specification

## Purpose
TBD - created by archiving change multi-filter-search. Update Purpose after archive.
## Requirements
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

### Requirement: Subset filters narrow the candidate pool via WHERE
Subset filters (datetime, geo, face) MUST be definite-membership filters that narrow the candidate set by contributing a `WHERE` predicate to a lazy SQL `Select`. They SHALL be composed as an intersect (AND) of all subset predicates at finalize.

Feature: image-search
Rule: subset predicates are commutative and compose by intersection

#### Scenario: Candidate count reflects only subset narrowing
- **GIVEN** an open search session
- **WHEN** the agent applies one or more subset filters
- **THEN** `candidate_count` is computed as `COUNT(*)` over the phase-1 `Select` built from the intersected subset predicates only
- **AND** any applied rank filters do not affect `candidate_count` (rank specs are excluded from the count and apply last)

#### Scenario: No image IDs materialize before finalize
- **GIVEN** a session with applied subset filters
- **WHEN** filters are applied but finalize has not yet run
- **THEN** the candidate set remains a SQL `Select` with predicates pushed down
- **AND** no image IDs are materialized into Python until the final `LIMIT K`

### Requirement: Rank filters are buffered and fused by Reciprocal Rank Fusion
Rank filters (CLIP similarity) SHALL emit a rank CTE rather than a `WHERE` predicate. All rank filters MUST be buffered and, at finalize, fused by Reciprocal Rank Fusion (RRF, `k=60`) into a score per image id. The candidate set MUST be the phase-1 subset-narrowed pool.

Feature: image-search
Rule: rank filters contribute (id, row_number) CTEs fused as SUM(weight/(k+rank))

#### Scenario: Finalize fuses multiple rank filters via RRF
- **GIVEN** a session with at least one applied rank filter (e.g. CLIP)
- **WHEN** the agent finalizes
- **THEN** each rank filter builds a rank CTE over the phase-1 candidate pool
- **AND** scores are fused with RRF using `k=60`
- **AND** hits are ordered by fused score descending, limited to Top-K

#### Scenario: Finalize skips RRF when there are no rank filters
- **GIVEN** a session with subset filters applied and zero rank filters
- **WHEN** the agent finalizes
- **THEN** RRF is skipped entirely
- **AND** the narrowed candidate set is returned ordered by `Image.id` with `score: null`

### Requirement: CLIP rank filter is implemented end-to-end
The `ClipRank` filter MUST accept a text query, compute the text embedding via the existing `get_text_embeddings`, and rank candidate images by `cosine_distance` over the existing `CLIP_Embedding` HNSW cosine index. The text query SHALL be stored in the filter spec; the vector MUST be recomputed at finalize.

Feature: image-search
Rule: CLIP ranking reuses the existing pgvector HNSW index

#### Scenario: CLIP rank uses the stored text query
- **GIVEN** a session with a `ClipRank` filter whose spec stores the text query
- **WHEN** the agent applies the filter and later finalizes
- **THEN** the text embedding is recomputed from the stored query at from_spec time
- **AND** ranking uses `CLIP_Embedding.embedding.cosine_distance(vec)` over the indexed column

### Requirement: Datetime, geo, and face filters are registered stubs
`DatetimeFilter`, `GeoFilter`, and `FaceFilter` MUST be registered in the filter registry so their contract and tool surface exist, but their `build_predicate` SHALL be unimplemented and rejected at add-time. EXIF metadata (`capture_time`, `latitude`, `longitude`) is now populated during ingestion, but filter query logic remains deferred.

Feature: image-search
Rule: stubs are advertised as not live and fail fast at add-time; underlying data columns are now populated

#### Scenario: A stub filter is rejected at add-time
- **GIVEN** a registered stub filter (datetime, geo, or face)
- **WHEN** the agent calls `POST /sessions/{id}/filters` with that filter kind
- **THEN** the API returns `501 Not Implemented`
- **AND** the spec is not appended to the session

#### Scenario: The registry advertises which filters are live
- **GIVEN** the filter registry
- **WHEN** the agent inspects available filters
- **THEN** `ClipRank` is advertised as live
- **AND** `DatetimeFilter`, `GeoFilter`, and `FaceFilter` are advertised as not implemented

### Requirement: Phase is derived at finalize, not stored
Tool-call order MUST be free; the two-phase execution (all subsets first, then all ranks) SHALL be enforced only inside finalize by bucketing filter specs by kind. The session MUST store no `phase` field.

Feature: image-search
Rule: phase is a function of the spec list, computed at finalize

#### Scenario: Mixed-order filter calls still produce correct two-phase execution
- **GIVEN** an open session where the agent applies a rank filter before a subset filter
- **WHEN** the agent finalizes
- **THEN** all subset predicates compose phase-1 regardless of call order
- **AND** all rank CTEs compose phase-2 and are fused over the phase-1 pool

### Requirement: EXIF metadata columns are populated during ingestion
The `Image` table SHALL include `capture_time` (TIMESTAMPTZ), `latitude` (DOUBLE PRECISION), and `longitude` (DOUBLE PRECISION) columns, populated during background processing by extracting EXIF metadata. All three fields SHALL be nullable and exposed in the `ImagePublic` API response schema. Datetime and offset tags SHALL be read from the ExifIFD sub-IFD (`0x8769`) as well as the top-level IFD, with sub-IFD values taking precedence, so `capture_time` is populated for real camera and phone files that store tags in the sub-IFD.

Feature: image-search
Rule: EXIF extraction runs during the existing process_upload_embeddings step; failures produce NULL rather than aborting ingestion

#### Scenario: Capture time is extracted from DateTimeOriginal + OffsetTimeOriginal
- **GIVEN** an uploaded image with EXIF `DateTimeOriginal` (0x9003) and `OffsetTimeOriginal` (0x9011) tags
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to the parsed datetime with the correct timezone offset

#### Scenario: Capture time is extracted from tags in the ExifIFD sub-IFD
- **GIVEN** an uploaded image whose `DateTimeOriginal`, `OffsetTimeOriginal`, `DateTimeDigitized`, and `OffsetTimeDigitized` tags are stored in the ExifIFD sub-IFD (`0x8769`) and not at the top level
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set from the sub-IFD `DateTimeOriginal` and `OffsetTimeOriginal` tags with the correct timezone offset

#### Scenario: Fallback to DateTimeDigitized when DateTimeOriginal is absent or incomplete
- **GIVEN** an uploaded image whose `DateTimeOriginal` tag is absent or lacks a matching offset, and that has `DateTimeDigitized` (0x9004) with `OffsetTimeDigitized` (0x9012)
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set using `DateTimeDigitized` as the fallback source

#### Scenario: Capture time is NULL when no datetime pair is complete
- **GIVEN** an uploaded image with `DateTimeOriginal` but no `OffsetTimeOriginal` and with no complete `DateTimeDigitized`/`OffsetTimeDigitized` pair
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to NULL

#### Scenario: Capture time is NULL when no datetime tags are present
- **GIVEN** an uploaded image with no EXIF datetime tags
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to NULL

#### Scenario: Embeddings are stored for the correct image when a batch contains an unreadable file
- **GIVEN** an uploaded batch containing a file the ingestion pipeline cannot open and other valid images
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** each valid image receives the embedding computed from itself
- **AND** no embedding is stored for the unreadable file

#### Scenario: GPS coordinates are extracted and validated
- **GIVEN** an uploaded image with EXIF GPS IFD containing valid latitude and longitude
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `latitude` and `longitude` are set to signed decimal degrees

#### Scenario: GPS coordinates are NULL when out of bounds
- **GIVEN** an uploaded image with EXIF GPS coordinates where latitude is outside [-90, 90] or longitude outside [-180, 180]
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** both `latitude` and `longitude` are set to NULL

#### Scenario: GPS coordinates are NULL when IFD is absent
- **GIVEN** an uploaded image with no EXIF GPS IFD
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** both `latitude` and `longitude` are set to NULL

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

### Requirement: EXIF fields are exposed in the ImagePublic API schema
The `ImagePublic` API response schema SHALL include `capture_time`, `latitude`, and `longitude` fields alongside existing fields.

Feature: image-search
Rule: new fields are nullable and match the column types

#### Scenario: ImagePublic response includes capture_time and geo fields
- **GIVEN** an image record with non-NULL `capture_time`, `latitude`, and `longitude`
- **WHEN** the API returns the image via `ImagePublic`
- **THEN** the response includes `capture_time` as an ISO-8601 timestamp with timezone
- **AND** `latitude` and `longitude` are returned as floats

