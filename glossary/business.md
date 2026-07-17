| Term | Definition | Use When | Avoid |
| --- | --- | --- | --- |
| Image Search | The capability letting a tool-driven agent retrieve images by combining subset and rank filters. | Naming the feature/capability. | Generic image lookup. |
| Candidate Pool | The running set of candidate image IDs after phase-1 subset intersection; size reported as `candidate_count`. | Discussing the pre-finalize candidate set. | The final output set. |
| Finalize | The action (`POST /finalize`) that runs phase-1 + phase-2 and returns the top-K hits; makes the session terminal. | Describing session completion. | Adding a filter. |
| Top-K | The `top_k` bounded number of final hits returned by finalize (default 100, unbounded max). | Sizing the final output. | Candidate pool size. |
