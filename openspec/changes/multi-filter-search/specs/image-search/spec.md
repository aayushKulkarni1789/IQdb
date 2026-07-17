## ADDED Requirements

### Requirement: Search session lifecycle
An agent creates a search session, applies filters in any order, then finalizes to obtain Top-K image hits. The session is terminal: once finalized it cannot accept more filters or be finalized again.

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

#### Scenario: Finalize a session and obtain Top-K hits
- **GIVEN** an open search session with zero or more applied filters
- **WHEN** the agent calls `POST /sessions/{id}/finalize`
- **THEN** the session's `finalized` flag is set to true
- **AND** the response returns `number_of_images_in_output` Top-K image hits

#### Scenario: A finalized session rejects further operations
- **GIVEN** a search session that has already been finalized
- **WHEN** the agent calls `POST /sessions/{id}/filters` or `POST /sessions/{id}/finalize` again
- **THEN** the API returns `409 Conflict`

### Requirement: Subset filters narrow the candidate pool via WHERE
Subset filters (datetime, geo, face) are definite-membership filters that narrow the candidate set by contributing a `WHERE` predicate to a lazy SQL `Select`. They are composed as an intersect (AND) of all subset predicates at finalize.

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
Rank filters (CLIP similarity) emit a rank CTE rather than a `WHERE` predicate. All rank filters are buffered and, at finalize, fused by Reciprocal Rank Fusion (RRF, `k=60`) into a score per image id. The candidate set is the phase-1 subset-narrowed pool.

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
The `ClipRank` filter accepts a text query, computes the text embedding via the existing `get_text_embeddings`, and ranks candidate images by `cosine_distance` over the existing `CLIP_Embedding` HNSW cosine index. The text query is stored in the filter spec; the vector is recomputed at finalize.

Feature: image-search
Rule: CLIP ranking reuses the existing pgvector HNSW index

#### Scenario: CLIP rank uses the stored text query
- **GIVEN** a session with a `ClipRank` filter whose spec stores the text query
- **WHEN** the agent applies the filter and later finalizes
- **THEN** the text embedding is recomputed from the stored query at from_spec time
- **AND** ranking uses `CLIP_Embedding.embedding.cosine_distance(vec)` over the indexed column

### Requirement: Datetime, geo, and face filters are registered stubs
`DatetimeFilter`, `GeoFilter`, and `FaceFilter` are registered in the filter registry so their contract and tool surface exist, but their `build_predicate` is unimplemented and rejected at add-time until the underlying ingestion (EXIF, PostGIS, face models) is built.

Feature: image-search
Rule: stubs are advertised as not live and fail fast at add-time

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
Tool-call order is free; the two-phase execution (all subsets first, then all ranks) is enforced only inside finalize by bucketing filter specs by kind. The session stores no `phase` field.

Feature: image-search
Rule: phase is a function of the spec list, computed at finalize

#### Scenario: Mixed-order filter calls still produce correct two-phase execution
- **GIVEN** an open session where the agent applies a rank filter before a subset filter
- **WHEN** the agent finalizes
- **THEN** all subset predicates compose phase-1 regardless of call order
- **AND** all rank CTEs compose phase-2 and are fused over the phase-1 pool
