# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | Objects created by agent tools and held in Agent Filter State. |
| SubsetFilter | `glossary/technical.md` | Predicate filters partitioned at finalize. |
| RankFilter | `glossary/technical.md` | Rank CTE filters partitioned at finalize. |
| CandidateQuery | `glossary/technical.md` | Lazy query built from partitioned filters. |
| Reciprocal Rank Fusion (RRF) | `glossary/technical.md` | Fusion scoring with k=60 at finalize. |
| SearchSession | `glossary/technical.md` | Persisted entity explicitly not used in v2. |
| Filter Spec | `glossary/technical.md` | Dict validated via from_spec inside tools. |
| FilterKind | `glossary/technical.md` | Closed enum governing tool exposure. |
| InvalidFilterSpecError | `glossary/technical.md` | Validation error reported back to LLM. |
| Agent Filter State | `glossary/technical.md` | Per-request in-memory filter list. |
| Finalize | `glossary/business.md` | Deterministic step after agent exit. |
| Top-K | `glossary/business.md` | Bounded result size via top_k. |
| Image Search | `glossary/business.md` | Capability replicated in agent-driven form. |
