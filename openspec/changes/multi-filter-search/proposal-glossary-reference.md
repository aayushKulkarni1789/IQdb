# Glossary Reference

| Term | Source Glossary | Context |
| --- | --- | --- |
| Filter | `glossary/technical.md` | The base search-filter abstraction (`a Filter abstraction`). |
| SubsetFilter | `glossary/technical.md` | `subset filters` that narrow the candidate set by definite membership. |
| RankFilter | `glossary/technical.md` | `rank filters` buffered then fused by RRF. |
| Reciprocal Rank Fusion | `glossary/technical.md` | How continuous rank-filter scores are fused. |
| SearchSession | `glossary/technical.md` | `a session that accumulates filter calls` (persisted JSONB row). |
| HNSW Cosine Index | `glossary/technical.md` | Existing pgvector index on `CLIP_Embedding.embedding`. |
| pgvector | `glossary/technical.md` | Vector storage/cosine-distance technology used by `ClipRank`. |
| Image Search | `glossary/business.md` | The `image-search` capability this change delivers. |
| Finalize | `glossary/business.md` | `a finalize that returns top-K hits` — session completion action. |
| Top-K | `glossary/business.md` | Number of final hits returned by finalize. |
