# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | D5/D6: each filter class gains a `FilterKind`, pydantic spec model, and `SPEC_EXAMPLE`. |
| CandidateQuery | `glossary/technical.md` | D7: finalize join to `image` keeps the lazy push-down model intact. |
| SearchSession | `glossary/technical.md` | D2: finalized sessions are the sweep's deletion target. |
| Filter Spec | `glossary/technical.md` | D5/D6: JSONB-persisted specs stay string-compatible while validation moves to pydantic models. |
| Cleanup Sweep | `glossary/technical.md` | New term defined by this design (D1–D4); the deletion mechanism for finished entities. |
| Terminal UploadJob | `glossary/technical.md` | New term; COMPLETED and DISCARD jobs are both sweep targets. |
| FilterKind | `glossary/technical.md` | New term; the StrEnum introduced in D5. |
| InvalidFilterSpecError | `glossary/technical.md` | New term; the 422-mapped spec-validation error in D6. |
| Ingestion Summary Log | `glossary/technical.md` | New term; the end-of-job observability line in D8. |
