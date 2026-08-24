# Council Notes: proposal.md

## Author Summary
Authored a revision of the primary draft: restructured the Why into five gap→consequence bullets, surfaced multi-worker sweep overlap and 500-rate alerting risks, tightened BREAKING markings, added a Specs line naming delta targets, and preserved all grill-me-locked decisions (summary counters, unconditional sweep of finished rows, FilterKind StrEnum + strict request field, pydantic spec models with from_validation formatter, finalize returning id/uri/score via PK join).

## Reviewer Challenges
- [blocker] Why-bullet claimed unknown filter kinds cause 500s today — false; `orchestrator.add_filter` already maps `UnknownFilterKindError` to 422.
- [blocker] Enum-keyed registry without str→enum conversion would raise `KeyError` on JSONB-deserialized string specs at runtime.
- [major] `UploadJobStatus.DISCARD` rows are terminal yet outside sweep scope; would accumulate forever.
- [major] "Sweep runs in tests" lacked a mechanism; hour-scale interval never fires during test runs, so behavior would go untested.
- [minor] "dimensions"/"gps" count semantics undefined; `InvalidFilterSpecError` location unnamed; lifespan handler doesn't exist today; new spec dirs not called out; disk-deletion race under multi-worker unnoted; no stance on v1 vs v2 for the additive hit field; sweep log levels unspecified.

## Resolutions
- Accepted: Rewrote kinds bullet to state the real gap (runtime-only enforcement; gains are schema-level validation, OpenAPI-documented enum); added explicit str→enum conversion in registry.from_spec; DISCARD jobs included in sweep scope after user approval; sweep pass defined as directly callable function for tests; defined grouped-field counting (extracted = all constituent columns persisted non-NULL); noted lifespan created from scratch; named new spec directories; added disk-race caveat on deferred file cleanup; pinned v1-with-additive-field stance; specified sweep log levels (INFO deletes / DEBUG empty / WARNING outage retry).
- Rejected: None — all challenges either improved accuracy or aligned with locked intent.
- Deferred: Exact default value of `SWEEP_INTERVAL_MINUTES` (hours-scale) to design.md.

## Remaining Risks
- Multi-worker deployments duplicate sweeps (wasted work only, documented).
- Finalized sessions become unrecoverable once swept — intended per user decision but worth re-confirming if any client later needs session replay.
- If disk cleanup is ever uncommented without coordination, concurrent workers could race on directory deletion.
