# Council Notes: proposal.md

## Author Summary
The proposal establishes a new API v2 sessionless agent-driven search workflow using LangChain 1.x ToolRuntime. The agent derives Filter objects from user_text, persists them in its in-memory state, and exits; the backend then finalizes via CandidateQuery/RRF. v1 is untouched. Core design decisions (agent state as list[Any] with replace semantics, only live filter kinds exposed, LLM via OpenAI-compatible base_url env-driven, thumbnail fn out of scope but implemented, specs additive-replica pattern) are distilled from the multi-session grill-me interview. The capabilities section lists agent-image-search as a new replica spec so the old image-search can later be deprecated.

## Reviewer Challenges
- Proposal references many implementation details (state typing, tool signatures, env vars) that are design-phase concerns — reviewer questions whether these belong at proposal level or should be deferred to design.md.
- The additive-replica spec pattern (writing a new requirement inside image-search delta so it can later replace the old) is unusual; reviewer seeks clarification on whether this creates duplication risk or spec drift.
- LLM env-var setup (llama.cpp base_url + Groq key) spans both llama.cpp and Groq integrations under a single `langchain-openai` dependency; reviewer asks whether a dedicated langchain-groq package is preferred for clarity.
- The proposal's "Impact" lists `openspec/specs/image-search/spec.md` as modified, but the new ADDED Requirement block lives in the change's own `specs/image-search/spec.md`; reviewer wants to verify the delta-spec format won't conflict with the main spec.
- No explicit migration plan is presented (there is none, since v2 is purely additive and v1 is untouched); reviewer asks whether this should be called out.

## Resolutions
- Accepted: All design decisions (state typing, tool signatures, env vars) are appropriately scoped to design.md and tasks.md; the proposal's role is architectural motivation + capability contract, not implementation detail.
- Accepted: The additive-replica pattern is intentional — the new Requirement block is self-contained inside the change's delta spec; it mirrors image-search sufficiently that once the new workflow is proven, the old session-based image-search can be deprecated and its delta spec removed. No duplication risk because the two specs diverge by design (sessionless vs session-based).
- Accepted: LLM integration uses `langchain-openai` with `model_provider="openai"` + `base_url`/`api_key` env vars; both llama.cpp (custom base_url, no key needed) and Groq (`https://api.groq.com/openai/v1` + key) are supported. No dedicated `langchain-groq` needed; the OpenAI-compatible path handles both.
- Accepted: The ADDED Requirement in the change's `specs/image-search/spec.md` is a standalone delta; it does not modify `openspec/specs/image-search/spec.md` (the main spec). The change's delta spec lives under `openspec/changes/.../specs/` and is independent. The main spec remains untouched; the new Requirement will later enable deprecating the main spec.
- Accepted: No migration plan is needed because v2 is purely additive on top of v1; v1 is left entirely untouched (no DB schema changes, no route removals). This is explicitly called out in the Impact section.

## Remaining Risks
- **Adoption path**: The proposal adds a parallel workflow. Acceptance requires that v1 continues to work unchanged until the new workflow is proven and optionally replaces it. Risk of two workflows coexisting without clear migration path for existing clients.
- **Spec drift**: The additive-replica requires ongoing maintenance to keep the two image-search specs in sync if behaviors diverge. Risk mitigated by noting in design that the replica is a stepping stone to deprecation.
- **LLM availability**: The workflow depends on an OpenAI-compatible endpoint (llama.cpp or Groq). Downtime or unreachability from the container blocks the entire search flow. Mitigation: clear 422/error messaging from tools and finalize.
- **Filter kind exposure**: Only clip and datetime are exposed as "live" via tools; geo and face remain stubs. If future work promotes geo/face, the tool set and state schema may need rethinking.