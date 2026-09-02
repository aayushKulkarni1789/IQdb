# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | Base abstraction for search filters split into SubsetFilter and RankFilter. |
| SubsetFilter | `glossary/technical.md` | WHERE-predicate filters narrowed in CandidateQuery phase-1. |
| RankFilter | `glossary/technical.md` | Rank CTE filters fused by RRF in phase-2. |
| CandidateQuery | `glossary/technical.md` | Lazy SQL push-down holding subset predicates and rank CTEs. |
| Reciprocal Rank Fusion (RRF) | `glossary/technical.md` | Fusion scoring with k=60 used at finalize. |
| SearchSession | `glossary/technical.md` | Persisted session entity that v2 replaces with in-memory state. |
| Filter Spec | `glossary/technical.md` | Serialized filter config round-tripped via to_spec/from_spec. |
| HNSW Cosine Index | `glossary/technical.md` | pgvector HNSW index on CLIP embeddings for ranking. |
| FilterKind | `glossary/technical.md` | Closed enumeration (CLIP, DATETIME, GEO, FACE) for registry lookup. |
| InvalidFilterSpecError | `glossary/technical.md` | Validation error formatted for agent recovery. |
| Agent Filter State | `glossary/technical.md` | Mutable per-request filter list held in LangChain agent state. |
| Cleanup Sweep | `glossary/technical.md` | Background pass that still owns finalized SearchSession deletion. |
| Image Search | `glossary/business.md` | Capability being served by the new v2 agent-driven route. |
| Finalize | `glossary/business.md` | Action that runs phase-1 + phase-2 and returns Top-K hits. |
| Top-K | `glossary/business.md` | Bounded number of hits returned by finalize. |
