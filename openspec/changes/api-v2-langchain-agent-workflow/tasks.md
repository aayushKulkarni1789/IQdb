## 1. Dependencies and Configuration

- [ ] 1.1 Add `langchain[openai]` to `backend/pyproject.toml` via `uv add --package app "langchain[openai]"` and verify `uv.lock` regeneration
- [ ] 1.2 Add LLM settings to `backend/app/core/config.py`: `LLM_BASE_URL: str`, `LLM_API_KEY: str = ""`, `LLM_MODEL: str`, `LLM_TEMPERATURE: float = 0.0`
- [ ] 1.3 Add LLM entries to `.env.example` (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_TEMPERATURE`) and update `docker-compose.yml` / `docker-compose.override.yml` to expose them to the backend service
- [ ] 1.4 Rebuild backend image and verify `uv sync --frozen --package app` installs `langchain` + `langchain-openai`

## 2. Agent State and Context

- [ ] 2.1 Create `backend/app/search/agent/state.py` with `FilterAgentState(AgentState)` holding `filters: list[Any] = []` (no reducer, replace semantics)
- [ ] 2.2 Create `backend/app/search/agent/context.py` that assembles deploy-time immutable filter descriptions from `REGISTRY` and each filter's `SPEC_FORMAT` / `SPEC_EXAMPLE` for use as system prompt and tool docstrings
- [ ] 2.3 Verify `FilterAgentState` does not coerce plain `Filter` objects through Pydantic (hold as `list[Any]`)

## 3. Agent Tools

- [ ] 3.1 Implement `add_clip_filter` in `backend/app/search/agent/tools.py` using `ToolRuntime`: validate spec via `registry.from_spec`, append `ClipRank` to `Agent Filter State` with `Command(update={"filters": next_list})`, report `InvalidFilterSpecError` back to LLM as string
- [ ] 3.2 Implement `add_datetime_filter` in `backend/app/search/agent/tools.py` with same pattern for `DatetimeFilter`
- [ ] 3.3 Implement `reset_filters` and `get_specs` tools: `reset_filters` replaces state with `[]`, `get_specs` returns `[f.to_spec() for f in filters]`
- [ ] 3.4 Verify only live `FilterKind` values (`clip`, `datetime`) are exposed as tools; `geo`/`face` omitted

## 4. LLM and Agent Factory

- [ ] 4.1 Create `backend/app/search/agent/llm.py` that builds the model via `init_chat_model(model_provider="openai", base_url=LLM_BASE_URL, api_key=LLM_API_KEY)` and `create_agent(model, tools, state_schema=FilterAgentState, system_prompt=...)`
- [ ] 4.2 Expose `invoke(user_text: str) -> dict` that runs the agent single-turn and returns final state containing `filters` and `messages`
- [ ] 4.3 Test agent construction against both a local `llama.cpp` base_url and `https://api.groq.com/openai/v1` (env-driven, no provider branching)

## 5. Finalize Helper

- [ ] 5.1 Create `backend/app/search/query.py` with `finalize(db: Session, filters: list[Filter], top_k: int) -> tuple[int, list[tuple[int, str, float | None]]]`
- [ ] 5.2 Implement partitioning into `SubsetFilter` vs `RankFilter` lists and delegation to `CandidateQuery(subset, rank).finalize(db, top_k)` without importing `SearchSession` or raising `HTTPException`
- [ ] 5.3 Verify `finalize` reuses same-kind OR / cross-kind AND and RRF `k=60` semantics by sharing `CandidateQuery` (ADR-0002/0003/0006)

## 6. Thumbnail Helper (staged)

- [ ] 6.1 Implement `make_thumbnail_jpeg(data: bytes, max_dim: int = 256) -> bytes` in `backend/app/core/thumbnails.py` using Pillow (longest edge -> `max_dim`, JPEG output)
- [ ] 6.2 Add unit tests for `make_thumbnail_jpeg` with synthetic images (portrait, landscape, small image already under `max_dim`)

## 7. API v2 Route

- [ ] 7.1 Create `backend/app/api/v2/main.py` router and `backend/app/api/v2/routes/query.py` with `POST /api/v2/search/query` accepting `{user_text: str, top_k: int = 100}`
- [ ] 7.2 Implement route flow: create agent, `invoke(user_text)`, read `state["filters"]`, return `422` if empty, else `finalize(db, filters, top_k)` and return `{number_of_images_in_output, hits: [{id, uri, score}]}`
- [ ] 7.3 Mount `api_v2_router` in `backend/app/main.py` alongside `api/v1` with prefix `/api/v2` and verify OpenAPI docs expose both versions

## 8. Tests

- [ ] 8.1 Write unit tests for agent tools: valid `add_clip_filter`/`add_datetime_filter` appends, malformed spec reports error without appending, `reset_filters` clears, `get_specs` round-trips
- [ ] 8.2 Write unit tests for `finalize(db, filters, top_k)` covering subset-only, rank-only, mixed, and same-kind union composition
- [ ] 8.3 Write integration test for `POST /api/v2/search/query`: valid query returns hits, empty filter list returns 422, `top_k` limits results

## 9. Verification

- [ ] 9.1 Run `openspec validate api-v2-langchain-agent-workflow --type change --strict` and fix any coherence errors
- [ ] 9.2 Run `make test` inside `docker compose` and verify all existing plus new tests pass
