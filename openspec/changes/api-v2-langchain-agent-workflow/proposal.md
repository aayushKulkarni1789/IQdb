## Why

The current v1 search workflow requires the client to manually decompose a natural-language intent into a sequence of filter specs (`POST /sessions`, repeated `POST /sessions/{id}/filters`), then finalize (`POST /sessions/{id}/finalize`). There is no way to submit a query like "photos from last summer in the mountains" directly — the client must figure out which filter kinds apply, assemble the spec, and call the endpoint repeatedly. We will add an agent-driven workflow that lets the frontend send `user_text` + `top_k` and have a LangChain agent derive and apply the filters.

## What Changes

- **New API version v2** under `backend/app/api/v2/`, mounted alongside v1 (v1 untouched and still used for ingestion + manual testing).
- **NEW**: Agent-driven single-turn route `POST /api/v2/search/query` accepting `{user_text, top_k}`.
- **NEW**: LangChain 1.x agent with custom `AgentState` whose `filters` channel holds a mutable list of **Filter objects** (subset + rank), scoped to the request — **no `SearchSession` DB row, no session id**.
- **NEW**: Tools running via `ToolRuntime`: `add_clip_filter`, `add_datetime_filter`, `reset_filters`, `get_specs`. Tools take a spec from the agent, construct a `Filter` via `from_spec` (validating), append to state, or report failure back to the LLM. Only live filter kinds (clip, datetime) are exposed.
- **NEW**: plain `finalize(db, filters: list[Filter], top_k)` that partitions the state's Filter objects into subset/rank and builds the existing `CandidateQuery` — decoupled from `SearchSession`/`HTTPException`.
- **LLM backend** is OpenAI-compatible via `langchain-openai`: llama.cpp (custom `base_url`) or Groq (`https://api.groq.com/openai/v1` + key), selected by env vars (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`). Single-turn; agent exits after deriving filters; backend then finalizes deterministically.
- Empty filter list after the agent run → HTTP 422.

## Capabilities

### New Capabilities
- `agent-image-search`: a sessionless agent-driven image search specification. The agent derives filter objects into in-memory state from `user_text`; backend finalizes via `CandidateQuery` RRF logic. Specifies the self-contained filter composition (same-kind OR, cross-kind intersect) and contract (filter kinds exposed via tools, only live kinds, empty-filter 422). This new specification is written as a replica of the existing `image-search` delta spec so the old session-based requirements can later be deprecated or deleted.

### Modified Capabilities
_(none — v1 behavior unchanged)_

## Impact

- `backend/pyproject.toml` + root `uv.lock` — add `langchain[openai]` (via `uv add --package app`); installed on backend image rebuild (`uv sync --frozen` already in Dockerfile).
- `backend/app/core/config.py` — add `LLM_BASE_URL: str`, `LLM_API_KEY: str = ""`, `LLM_MODEL: str`, `LLM_TEMPERATURE: float = 0`.
- `.env.example` + `docker-compose(.override).yml` — new LLM env vars (LLM_BASE_URL kept in `.env.example`).
- `backend/app/search/agent/` (new) — state, tools, llm/agent factory.
- New `backend/app/search/query.py` — `finalize(db, filters, top_k)`.
- New `backend/app/api/v2/` — router + `routes/query.py`.
- `backend/app/main.py` — include v2 router.
- `backend/tests/` — new tests for agent tools, finalize-from-filters, v2 route.
- `openspec/specs/image-search/spec.md` — new ADDED Requirement block (replica of session-based surface, additive only, so old spec can later be deprecated).

## File changes (new files)

- `openspec/changes/api-v2-langchain-agent-workflow/proposal.md`
- `openspec/changes/api-v2-langchain-agent-workflow/design.md`
- `openspec/changes/api-v2-langchain-agent-workflow/tasks.md`
- `openspec/changes/api-v2-langchain-agent-workflow/specs/image-search/spec.md` (ADDED Requirements)
- `openspec/changes/api-v2-langchain-agent-workflow/proposal.council.md` (adversarial-authoring, created after writing proposal.md)
- `glossary/technical.md` — add **Agent Filter State** term
- `backend/app/search/agent/state.py` (new)
- `backend/app/search/agent/tools.py` (new)
- `backend/app/search/agent/llm.py` (new)
- `backend/app/search/agent/context.py` (new)
- `backend/app/search/query.py` (new)
- `backend/app/api/v2/main.py` (new)
- `backend/app/api/v2/routes/query.py` (new)
- `backend/app/core/thumbnails.py` (new, thumbnail fn only)
- `backend/tests/` — new test files