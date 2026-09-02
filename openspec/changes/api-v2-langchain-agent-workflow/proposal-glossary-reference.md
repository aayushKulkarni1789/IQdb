# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | Base abstraction added to agent state via ToolRuntime tools. |
| SubsetFilter | `glossary/technical.md` | Membership filter type available through datetime tool. |
| RankFilter | `glossary/technical.md` | Scoring filter type available through CLIP tool. |
| CandidateQuery | `glossary/technical.md` | Lazy SQL object built from agent state at finalize. |
| Reciprocal Rank Fusion (RRF) | `glossary/technical.md` | Fusion method referenced for future multi-rank support. |
| SearchSession | `glossary/technical.md` | Persisted session entity that v2 deliberately avoids. |
| Filter Spec | `glossary/technical.md` | Serialized form validated via from_spec inside tools. |
| FilterKind | `glossary/technical.md` | Closed enumeration governing which tools are exposed. |
| InvalidFilterSpecError | `glossary/technical.md` | Error type surfaced back to LLM on bad specs. |
| Agent Filter State | `glossary/technical.md` | In-memory filter list that is the v2 session replacement. |
| Image Search | `glossary/business.md` | Capability served by the new agent-driven route. |
| Finalize | `glossary/business.md` | Deterministic step after the agent exits. |
| Top-K | `glossary/business.md` | Bounded result size requested via top_k. |
