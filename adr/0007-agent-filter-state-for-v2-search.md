# Agent Filter State and OpenAI-compatible LLM for v2 search

- Status: accepted
- Date: 2026-09-02

## Context and Problem Statement

`api/v1` search is a persisted, multi-call lifecycle: create a `SearchSession` row, append filter specs via repeated HTTP calls, then finalize. The client must decompose natural-language intent into specs. For an agent-driven alternative we need a per-request place to accumulate filters, and a single env-driven way to run the same agent against a local `llama.cpp` server and against **Groq**, without introducing provider-specific code or a new persisted session table.

## Considered Options

- Keep accumulating specs in a persisted `SearchSession` and have the agent call the existing session endpoints internally.
- Hold derived filters only in a per-request in-memory list owned by the LangChain agent, with no DB row and no session id; partition into subset vs rank only at a new `finalize(db, filters, top_k)` helper.
- For the LLM, adopt provider-specific packages (`langchain-groq` plus a local provider) with branching logic, vs. a single `langchain-openai` OpenAI-compatible interface parameterized by `base_url` / `api_key` env vars.

## Decision Outcome

Chosen option: in-memory **Agent Filter State** (`filters: list[Any]` on `FilterAgentState(AgentState)`) mutated via `ToolRuntime` `Command(update=...)` replace semantics, and a single `langchain-openai` integration using `init_chat_model(model_provider="openai", base_url=LLM_BASE_URL, api_key=LLM_API_KEY)`. Tools validate specs with `registry.from_spec` and report failures back to the LLM; no DB access occurs inside the agent loop. The route creates the agent, invokes it on `user_text`, reads `state["filters"]`, and calls the new `finalize` which builds `CandidateQuery` from those objects. The new `api/v2` router is additive; `api/v1`, `SearchSession`, and the **Cleanup Sweep** (ADR-0004) remain in force and unchanged.

### Consequences

- Good, because filter accumulation is request-scoped, needs no migration, and keeps the lazy **CandidateQuery** / **Reciprocal Rank Fusion (RRF)** contracts (ADR-0001–ADR-0003, ADR-0006) unchanged — the new `finalize` merely supplies objects instead of re-parsed JSONB.
- Good, because one LLM dependency covers both `llama.cpp` and **Groq** via env; switching providers is a config change, not a code change.
- Good, because `api/v2` can be rolled back by unmounting its router without touching the shared domain layer.
- Bad, because **Filter** objects in agent state are not JSON-serializable or checkpoint-safe; any future checkpoint/persistence of agent state would require a serialization layer.
- Bad, because the agent has no live `candidate_count` feedback (tools do not query the DB), which may reduce its ability to self-correct within the single turn.
