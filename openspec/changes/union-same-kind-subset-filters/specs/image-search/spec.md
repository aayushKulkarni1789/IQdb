## MODIFIED Requirements

### Requirement: Subset filters narrow the candidate pool via WHERE
Subset filters (datetime, geo, face) MUST be definite-membership filters that narrow the candidate set by contributing a `WHERE` predicate to a lazy SQL `Select`. They SHALL be composed using union-then-intersect: subset filters of the same kind are composed with OR (union), and the resulting per-kind predicates are composed with AND (intersect) across different kinds.

Feature: image-search
Rule: same-kind subset filters union, cross-kind subset filters intersect

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

#### Scenario: Multiple same-kind subset filters compose with OR
- **GIVEN** an open search session
- **WHEN** the agent applies two subset filters of the same kind (e.g. two datetime range filters)
- **THEN** the predicates are composed with OR so that images matching either range are included in the candidate set
- **AND** `candidate_count` reflects the union of matching images, not the intersection

#### Scenario: Cross-kind subset filters compose with AND
- **GIVEN** an open search session
- **WHEN** the agent applies subset filters of different kinds (e.g. one datetime filter and one geo filter)
- **THEN** the per-kind OR groups are composed with AND so that images must satisfy all kind groups
