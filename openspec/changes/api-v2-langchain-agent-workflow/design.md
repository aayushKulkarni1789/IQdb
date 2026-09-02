## Context

The current search path is fully session-based. A client creates a **SearchSession** row, repeatedly calls `POST /sessions/{id}/filters` with a **Filter Spec**, then calls `finalize` to obtain **Top-K** hits. The server persists every spec in JSONB, mediates the **FilterKind** enumeration, and enforces **SubsetFilter** / **RankFilter** phases through **CandidateQuery** (ADR-0001, ADR-0002). Ranking is fused by **Reciprocal Rank Fusion (RRF)** with `k=60` (ADR-0003), and cleanup is owned by the **Cleanup Sweep** (ADR-0004).

There is no way for a frontend to send free-form `user_text` like "photos from last summer showing a beach at sunset" and have the backend turn it into filters. That decomposition is the client's burden. The project now needs an agent-driven alternative that keeps the existing filter engine but moves intent parsing into the backend, while leaving `api/v1` untouched for ingestion and manual testing. The agent must run synchronously (the stack is sync SQLModel/psycopg), use LangChain 1.x **ToolRuntime** to mutate its own state, and choose its LLM from env so the same code runs against a local `llama.cpp` server or **Groq** via an OpenAI-compatible endpoint.

The shared domain layer (`filter.py`, `filters/`, `registry.py`, `CandidateQuery`) is not version-coupled; it can be imported by both `api/v1` and the new `api/v2`. Only the orchestration and HTTP surface need a new shape.

## Goals / Non-Goals

**Goals:**
- Add `POST /api/v2/search/query` that accepts `{user_text, top_k}` and returns ranked hits by running an LLM agent to completion, then a deterministic filter finalize.
- Hold the derived filters only in a per-request **Agent Filter State** — a mutable in-memory list of **Filter** objects — scoped to the agent run; no **SearchSession** row, no session id.
- Reuse the existing **Filter**, **SubsetFilter**, **RankFilter**, **Filter Spec**, and **CandidateQuery** machinery; partitions into subset vs rank occur only inside the new `finalize` helper.
- Drive the LLM from env so `llama.cpp` and **Groq** are interchangeable without code change.

**Non-Goals:**
- Modifying or deprecating `api/v1` routes, **SearchSession**, or **Cleanup Sweep** in this change.
- Implementing storage fetch (`uri -> bytes`) or wiring thumbnails into the v2 response — a standalone thumbnail helper is implemented but not yet served.
- Supporting geo/face filters — they remain stubs and are not exposed as agent tools.
- Streaming, multi-turn refinement, or persistent agent memory.

## Decisions

### D1: In-memory agent state replaces the persisted session

Introduce `Agent Filter State`: `filters: list[Any]` on a `FilterAgentState(AgentState)` subclass. The field is typed as `list[Any]` so LangChain/LangGraph does not try to coerce plain **Filter** objects through Pydantic (they are not `BaseModel`s). Tools read `runtime.state["filters"]`, compute the full next list, and return `Command(update={"filters": next_list})` which replaces the channel — no reducer, full-list replace semantics. Single-turn, request-scoped, never persisted.

**Alternatives considered:** `list[Filter]` with a reducer or a `Spec`-holding list re-parsed with `from_spec` at **Finalize**. Rejected — reducer merge is unnecessary when tools produce the complete list, and round-tripping through JSON adds validation cost that tools already paid.

### D2: Tools are pure state mutators with no DB access

Four tools via **ToolRuntime**: `add_clip_filter`, `add_datetime_filter`, `reset_filters`, `get_specs`. Each `add_*` receives a spec dict from the agent, calls `registry.from_spec(spec)` to validate and construct a **Filter** object (`ClipRank` or `DatetimeFilter`), and appends it; `reset_filters` replaces state with `[]`; `get_specs` returns `[f.to_spec() for f in filters]`. Failures are reported back to the LLM as a string message; no `candidate_count` is computed inside the agent. Only the post-agent `finalize` touches the database.

**Alternatives considered:** Letting tools call `CandidateQuery.candidate_count` for live feedback. Rejected — couples the agent loop to the database and adds a read per tool call; validation-only tools are simpler and keep the agent deterministic.

### D3: A thin `finalize(db, filters, top_k)` decouples search from HTTP/session

New helper `finalize(db: Session, filters: list[Filter], top_k: int) -> (int, list[(id, uri, score)])` lives beside the existing orchestrator (e.g. `app/search/query.py`). It partitions `filters` by `isinstance(f, RankFilter)` vs `SubsetFilter`, constructs `CandidateQuery(subset, rank)`, and calls `CandidateQuery.finalize`. No import of `SearchSession`, no `HTTPException`.

**Rationale:** mirrors `orchestrator._build_candidate_query` but operates on objects the agent already produced. Existing orchestrator functions remain for v1; the new helper is free of session lifecycle concerns.

### D4: LLM via `langchain-openai` OpenAI-compatible interface

Add `langchain[openai]`. Build the model with `init_chat_model(model, model_provider="openai", base_url=LLM_BASE_URL, api_key=LLM_API_KEY)` and pass it to `create_agent(model, tools, state_schema=FilterAgentState, system_prompt=...)`. The same code serves `llama.cpp` (`base_url` points at the local server, key unused) and **Groq** (`base_url = https://api.groq.com/openai/v1`, key set). `LLM_BASE_URL` is kept in `.env.example`; other LLM settings are `LLM_MODEL` and `LLM_TEMPERATURE`.

**Alternatives considered:** `langchain-groq` plus a separate local provider package. Rejected — both endpoints are OpenAI-compatible; one dependency covers both and keeps the switch env-driven.

### D5: v2 as a parallel parallel router under `/api/v2`

Create `backend/app/api/v2/main.py` (router) and `routes/query.py`. Mount alongside `api/v1` in `app/main.py`. Shared domain modules (`app/search/filter.py`, `filters/`, `registry.py`, `schemas.py`) are imported directly; no copy is needed. The route flow is:

```
POST /api/v2/search/query {user_text, top_k}
  -> create_agent(...).invoke({"messages": user_text})
  -> filters = result["filters"]
  -> if not filters: 422
  -> count, hits = finalize(db, filters, top_k)
  -> return {number_of_images_in_output, hits}
```

Only live **FilterKind** values (`clip`, `datetime`) are exposed as tools; geo/face are omitted so the agent cannot produce a non-live filter.

### D6: Thumbnail helper implemented but not wired

Implement `make_thumbnail_jpeg(data: bytes, max_dim=256) -> bytes` in `backend/app/core/thumbnails.py` (Pillow resize on the longest edge, JPEG output, tests covered). Storage fetch (`fetch_image_bytes(uri: str) -> bytes`) is out of scope and is not called from the v2 route this change; the route therefore returns hits without thumbnails per the proposal note. Wiring fetch + thumbnail into the response is a follow-up change.

### D7: Deploy-time immutable filter descriptions as context

Live filter type descriptions (`SPEC_FORMAT` / `SPEC_EXAMPLE` per **Filter**, plus `REGISTRY` advertising) are assembled once at startup (e.g. `app/search/agent/context.py`) and supplied as the agent's `system_prompt` plus tool docstrings. They are not passed as mutable message content or per-request state.

### D8: Config and dependency delivery

Add `LLM_BASE_URL: str`, `LLM_API_KEY: str = ""`, `LLM_MODEL: str`, `LLM_TEMPERATURE: float = 0.0` to `app/core/config.py`. Add matching entries to `.env.example` and to `docker-compose.yml/.override.yml` `environment`/`env_file` so containers see them. Add `langchain[openai]` to workspace `pyproject.toml` via `uv add --package app`; `uv.lock` is regenerated and the backend image rebuild already runs `uv sync --frozen --package app`.

## Risks / Trade-offs

- **[LLM unavailability]** The agent depends on a reachable OpenAI-compatible endpoint. If `llama.cpp` or the **Groq** network is down, every query fails. -> Mitigated by surfacing tool validation errors to the LLM for recovery attempts within the single turn, and by returning a clear 500 for outright model errors; env defaults documented in `.env.example`.
- **[Plain objects in state]** **Filter** instances are not JSON-serializable and not checkpoint-safe. Persisting or serializing agent state would break. -> Accepted because state is request-scoped and single-turn; no checkpoint or persistence is used. Typing as `list[Any]` avoids Pydantic coercion.
- **[Two parallel APIs]** `api/v1` and `api/v2` coexist. Drift between their filter semantics is possible. -> Mitigated by sharing the domain layer (`CandidateQuery`, **FilterKind**, **Reciprocal Rank Fusion (RRF)**) and by specifying the new behavior as a self-contained **Agent Filter State** capability that mirrors the existing `image-search` contract, so one can later be deprecated cleanly.
- **[No candidate count feedback]** Tools do not return `candidate_count`, unlike the session path. The agent therefore cannot observe narrowing. -> Accepted as a simplicity trade; the deterministic **Finalize** is still checked by tests; feedback can be reintroduced later behind a read-only tool if needed.
- **[Thumbnail not served]** `make_thumbnail_jpeg` exists but the v2 response contains no thumbnails until fetch is implemented. -> Documented as a staged delivery; no partial wiring is shipped.

## Migration Plan

1. Merge proposal + design + specs; run `uv add --package app "langchain[openai]"` and rebuild the backend image (`docker compose build backend`).
2. Add LLM env entries to `.env` (copy from `.env.example`); set `LLM_BASE_URL` to either local `llama.cpp` or `https://api.groq.com/openai/v1` and `LLM_API_KEY` accordingly.
3. Deploy. No database migration. No `api/v1` change. Rollback is just reverting the new `api/v2` router and LLM config; shared domain code is unaffected.
4. Follow-up change wires `fetch_image_bytes` and returns thumbnails in the v2 response; a later change can deprecate `api/v1` search routes once `api/v2` is proven.

## Open Questions

- None. The choice to keep filter-type descriptions immutable at deploy time vs. per-request is settled (deploy-time context); any future need to make them mutable would be handled by a new superseding ADR.
