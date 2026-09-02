## ADDED Requirements

### Requirement: Agent-driven search via Agent Filter State

The system SHALL expose `POST /api/v2/search/query` accepting `{user_text: string, top_k: int}`. The request SHALL invoke a single-turn LangChain agent that derives zero or more **Filter** objects into an in-memory **Agent Filter State** (`filters: list[Any]`) scoped to the request. After the agent exits, the backend SHALL call `finalize(db, filters, top_k)` to obtain **Top-K** hits. No **SearchSession** row or session id is created. Only live **FilterKind** values are exposed as tools.

Feature: agent-image-search
Rule: user_text is decomposed only by the agent; the backend finalize is deterministic and sessionless

#### Scenario: A natural-language query produces filters and returns hits
- **GIVEN** an agent with tools `add_clip_filter`, `add_datetime_filter`, `reset_filters`, `get_specs` and a request `{user_text: "photos from last summer showing a beach at sunset", top_k: 10}`
- **WHEN** the agent is invoked and appends a **ClipRank** and a **DatetimeFilter** to **Agent Filter State**, then the backend calls `finalize(db, filters, top_k)`
- **THEN** the response returns `number_of_images_in_output` **Top-K** hits each with `id`, `uri`, and `score`

#### Scenario: Filters live only in agent state and never in the database
- **GIVEN** a `POST /api/v2/search/query` request
- **WHEN** the agent derives filters
- **THEN** the filters exist only as **Filter** objects in **Agent Filter State**
- **AND** no **SearchSession** row is created

#### Scenario: Only live filter kinds are exposed through agent tools
- **GIVEN** the **FilterKind** registry where only `clip` and `datetime` are live
- **WHEN** the agent is given its tool set
- **THEN** only `add_clip_filter` and `add_datetime_filter` (plus `reset_filters` and `get_specs`) are available
- **AND** no tool for `geo` or `face` is exposed

#### Scenario: An empty derived filter list is rejected
- **GIVEN** a request where the agent appends no filters to **Agent Filter State**
- **WHEN** the backend attempts to finalize
- **THEN** the API returns `422 Unprocessable Entity`

#### Scenario: The agent can reset and inspect its own state
- **GIVEN** an agent that previously appended filters
- **WHEN** it calls `reset_filters`
- **THEN** **Agent Filter State** is replaced with `[]`
- **AND** a subsequent `get_specs` returns `[]`
- **AND** a `get_specs` after appending returns the specs of the current filters via `to_spec()`

### Requirement: Subset and rank composition matches the shared filter engine

**SubsetFilter** predicates and **RankFilter** CTEs accumulated in **Agent Filter State** SHALL be composed by `finalize` exactly as in the shared engine: same-kind **SubsetFilter** predicates are unioned with `OR`, cross-kind groups are intersected with `AND`, and **RankFilter** CTEs are fused by **Reciprocal Rank Fusion (RRF)** with `k=60`. The candidate set remains a lazy **CandidateQuery** until the final `LIMIT K`.

Feature: agent-image-search
Rule: v2 finalize reuses CandidateQuery composition and RRF unchanged

#### Scenario: Multiple same-kind subset filters compose with OR
- **GIVEN** **Agent Filter State** containing two **DatetimeFilter** objects covering disjoint date ranges
- **WHEN** `finalize(db, filters, top_k)` partitions them into subset filters and builds **CandidateQuery**
- **THEN** the candidate set includes images matching either range (union)

#### Scenario: Cross-kind subset filters compose with AND
- **GIVEN** **Agent Filter State** containing one **DatetimeFilter** and one **ClipRank** where only **DatetimeFilter** is a **SubsetFilter**
- **WHEN** `finalize` builds **CandidateQuery**
- **THEN** the clips rank only over the datetime-narrowed pool (subset intersect, then rank)

#### Scenario: Multiple rank filters are fused by RRF
- **GIVEN** **Agent Filter State** containing two **RankFilter** objects
- **WHEN** `finalize` builds rank CTEs and fuses them
- **THEN** scores are `SUM(weight / (60 + rank))` grouped by `id`, ordered descending, limited to **Top-K**

#### Scenario: Finalize without rank filters returns score null ordered by id
- **GIVEN** **Agent Filter State** containing only **SubsetFilter** objects
- **WHEN** `finalize` runs with no **RankFilter**
- **THEN** hits are returned ordered by `Image.id` with `score: null`

### Requirement: Malformed filter specs are reported to the LLM, not persisted

A tool call carrying a valid **FilterKind** but missing or mistyped fields SHALL be rejected inside the tool via `InvalidFilterSpecError` formatting and returned to the LLM as a message describing the problems, the expected format, and a concrete example. No **Filter** is appended. Unknown extra fields SHALL be ignored via `extra="ignore"` on the spec model.

Feature: agent-image-search
Rule: validation feedback stays in the agent loop; no partial state is stored

#### Scenario: A CLIP spec missing the text query is reported to the agent
- **GIVEN** an agent that calls `add_clip_filter` with `{"kind": "clip"}` and no `text`
- **WHEN** the tool validates via `from_spec`
- **THEN** the tool returns a message listing field problems, the expected CLIP format, and an example
- **AND** **Agent Filter State** is unchanged

#### Scenario: Extra fields in a spec are ignored
- **GIVEN** an agent that calls `add_datetime_filter` with a valid spec plus unknown extra fields
- **WHEN** the tool validates
- **THEN** the **Filter** is created and appended with extra fields ignored

### Requirement: LLM is selected from env via an OpenAI-compatible endpoint

The agent LLM SHALL be constructed via `langchain-openai` using `init_chat_model(model_provider="openai", base_url=LLM_BASE_URL, api_key=LLM_API_KEY)` with `LLM_MODEL` and `LLM_TEMPERATURE` from settings. `LLM_BASE_URL` is documented in `.env.example` and supports both a local `llama.cpp` server and `https://api.groq.com/openai/v1`.

Feature: agent-image-search
Rule: one dependency covers both local and hosted inference

#### Scenario: Local inference via llama.cpp
- **GIVEN** `LLM_BASE_URL` pointing at a local OpenAI-compatible server and an empty `LLM_API_KEY`
- **WHEN** the agent is constructed
- **THEN** it connects via the OpenAI-compatible interface without requiring a key

#### Scenario: Hosted inference via Groq
- **GIVEN** `LLM_BASE_URL=https://api.groq.com/openai/v1` and `LLM_API_KEY` set
- **WHEN** the agent is constructed
- **THEN** it authenticates via the same OpenAI-compatible interface

### Requirement: Thumbnail helper is available but not yet served in v2

The codebase SHALL provide `make_thumbnail_jpeg(data: bytes, max_dim: int = 256) -> bytes` that resizes the longest edge to `max_dim` and returns JPEG bytes. Storage fetch (`uri -> bytes`) is out of scope. `POST /api/v2/search/query` therefore returns hits without thumbnails in this change; wiring fetch plus thumbnail into the response is a follow-up.

Feature: agent-image-search
Rule: thumbnail generation staged separately from storage access

#### Scenario: Thumbnail helper resizes correctly
- **GIVEN** raw image bytes for a large image
- **WHEN** `make_thumbnail_jpeg` is called
- **THEN** the returned bytes decode as JPEG with longest edge `<= 256`

#### Scenario: v2 query returns hits without thumbnails in this change
- **GIVEN** a successful `POST /api/v2/search/query`
- **WHEN** the response is returned
- **THEN** each hit contains `id`, `uri`, and `score` and no thumbnail field is required
