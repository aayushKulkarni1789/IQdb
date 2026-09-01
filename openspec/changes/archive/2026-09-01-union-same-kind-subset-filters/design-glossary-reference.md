# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | Base abstraction split into SubsetFilter and RankFilter |
| SubsetFilter | `glossary/technical.md` | Filters composing via WHERE predicates, grouped by kind for union |
| CandidateQuery | `glossary/technical.md` | Lazy SQL push-down object being modified to group subset predicates |
| FilterKind | `glossary/technical.md` | StrEnum used as grouping key for subset filter composition |
| Reciprocal Rank Fusion (RRF) | `glossary/technical.md` | Phase-2 scoring, unchanged by this design |
| SearchSession | `glossary/technical.md` | Persisted entity whose specs are reconstructed with new composition |
