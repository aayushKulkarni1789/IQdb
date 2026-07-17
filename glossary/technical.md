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
