# ADR Review Manifest

- Status: completed
- Review date: 2026-09-02

## Review Summary

ADR review completed for this change. Design decisions were checked against all in-force ADRs. One new durable decision — the per-request **Agent Filter State** replacing the persisted **SearchSession** for `api/v2` and the single OpenAI-compatible LLM provider — was distilled into a repository-level ADR.

## In-Force ADRs Reviewed

- `adr/0001-filter-subset-rank-taxonomy.md` — accepted; in force
- `adr/0002-lazy-sql-pushdown-candidatequery.md` — accepted; in force
- `adr/0003-reciprocal-rank-fusion.md` — accepted; in force
- `adr/0004-cleanup-sweep-for-finished-entities.md` — accepted; in force
- `adr/0005-store-capture-time-as-naive-local-time.md` — accepted; in force
- `adr/0006-union-same-kind-subset-filters.md` — accepted; in force

No ADR supersedes another; all six remain in force. Design D3 (`finalize` partitioning), D1 (**Agent Filter State** vs **SearchSession**), and D4 (LLM via `langchain-openai`) are coherent with this set — subset/rank taxonomy, lazy `CandidateQuery`, RRF, and same-kind union semantics are reused unchanged.

## New Durable ADRs Created

- `adr/0007-agent-filter-state-for-v2-search.md` — agent-driven v2 search uses per-request **Agent Filter State** (in-memory `Filter` list, no DB row) mutated via `ToolRuntime`, and a single OpenAI-compatible LLM interface (`langchain-openai` with `LLM_BASE_URL`/`LLM_API_KEY`) for both `llama.cpp` and **Groq**. The new `api/v2` router is additive; `api/v1` and existing ADRs remain in force.
