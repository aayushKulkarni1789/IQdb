| Term | Definition | Use When | Avoid |
| --- | --- | --- | --- |
| Filter | The base abstraction in `backend/app/search` that a tool call adds to a search session; split into SubsetFilter and RankFilter. | Referring to the search filter abstraction, not a generic HTTP/DB filter. | Generic "filter" meaning any narrowing operation. |
| SubsetFilter | A Filter that contributes a SQL `WHERE` predicate narrowing the candidate set by definite membership. | Describing datetime/geo/face-style membership filters. | Rank/similarity filters. |
| RankFilter | A Filter that contributes a rank CTE for continuous scoring, fused by RRF at finalize. | Describing CLIP-style similarity filters. | Boolean membership filters. |
| CandidateQuery | In-memory object holding the universe `select(Image.id)`, subset predicates, and rank filters; never persisted. | Discussing lazy SQL push-down of the candidate set. | Materialized ID lists. |
| Reciprocal Rank Fusion (RRF) | Scoring method `score = Σ weight/(k + rank)` that fuses multiple rank filters; `k = 60`. | Explaining how rank filters combine. | Simple score averaging. |
| SearchSession | Postgres row (`id`, `specs` JSONB, `finalized`, `created_at`) accumulating filter calls for one search. | Referring to the persisted session entity. | A transient in-memory session. |
| Filter Spec | Serialized filter config stored in `SearchSession.specs`, round-tripped via `to_spec()`/`from_spec()`. | Discussing JSONB persistence of a filter. | OpenSpec "spec" change artifacts. |
| HNSW Cosine Index | The pgvector HNSW index on `CLIP_Embedding.embedding` (`vector_cosine_ops`) used for CLIP ranking. | Mentioning the embedding index. | Generic ANN index. |
| pgvector | Postgres extension providing the `VECTOR(512)` type and cosine distance used for embeddings. | Naming the vector storage technology. | A generic vector database. |
| Cleanup Sweep | The periodic in-process background pass that unconditionally deletes finalized SearchSession rows and terminal UploadJob rows. | Discussing finished-entity deletion; never call it TTL (Postgres has none). | "TTL", retention window, cron job. |
| Terminal UploadJob | An UploadJob in status COMPLETED or DISCARD; both are final states eligible for sweep deletion. | Deciding what the sweep may delete. | Open or in-flight jobs. |
| FilterKind | The StrEnum (CLIP, DATETIME, GEO, FACE) naming filter kinds; registry key and request-validation type. | Typing filter kinds in code and API schemas. | Bare string kinds. |
| InvalidFilterSpecError | The ValueError raised when a filter spec has a valid kind but malformed fields; formats agent-actionable messages via from_validation. | Explaining 422 responses for bad filter specs. | Raw KeyError/500s. |
| Agent Filter State | The mutable per-request list of Filter objects held in LangChain agent state that replaces the DB SearchSession in the v2 workflow. | Referring to the in-memory filter list owned by the agent during a single query. | Persisted SearchSession rows. |
| Ingestion Summary Log | The single end-of-job INFO line reporting totals, per-field metadata extraction counts, elapsed time, and status of an ingestion task. | Referring to ingestion observability output. | Per-image logging. |
