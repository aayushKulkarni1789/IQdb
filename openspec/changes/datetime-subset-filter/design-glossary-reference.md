# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| SubsetFilter | `glossary/technical.md` | DatetimeFilter extends SubsetFilter to emit WHERE predicates over capture_time |
| RankFilter | `glossary/technical.md` | Referenced in Context section — rank filters remain unchanged in this design |
| CandidateQuery | `glossary/technical.md` | Lazy SQL push-down that DatetimeFilter predicates integrate with |
| FilterKind | `glossary/technical.md` | DATETIME enum value used as registry key and spec discriminator |
| Filter Spec | `glossary/technical.md` | DatetimeFilterSpec is the serialized config stored in SearchSession.specs JSONB |
| Reciprocal Rank Fusion (RRF) | `glossary/technical.md` | Referenced — DatetimeFilter does not affect RRF (subset-only) |
| SearchSession | `glossary/technical.md` | Persists datetime filter specs in ordered JSONB log |
| InvalidFilterSpecError | `glossary/technical.md` | Raised when DatetimeFilterSpec validation fails (inverted ranges) |
