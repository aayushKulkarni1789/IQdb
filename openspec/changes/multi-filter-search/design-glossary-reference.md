# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | Base abstraction split into SubsetFilter and RankFilter. |
| SubsetFilter | `glossary/technical.md` | Emits a `WHERE` predicate; datetime/geo/face style. |
| RankFilter | `glossary/technical.md` | Emits a rank CTE; CLIP-style similarity. |
| CandidateQuery | `glossary/technical.md` | In-memory lazy SQL push-down of the candidate set. |
| Reciprocal Rank Fusion | `glossary/technical.md` | `k=60` fusion of rank filters at finalize. |
| SearchSession | `glossary/technical.md` | Persisted JSONB session row; terminal after finalize. |
| Filter Spec | `glossary/technical.md` | Serialized filter config in `SearchSession.specs`. |
| HNSW Cosine Index | `glossary/technical.md` | Index `ClipRank` ranks over. |
| pgvector | `glossary/technical.md` | Vector extension; stack unchanged. |
| Image Search | `glossary/business.md` | Capability this design implements. |
| Candidate Pool | `glossary/business.md` | Running candidate set; size reported as `candidate_count`. |
| Finalize | `glossary/business.md` | Action that runs phase-1+phase-2 and returns Top-K. |
| Top-K | `glossary/business.md` | `top_k` bounded final output size (default 100). |
