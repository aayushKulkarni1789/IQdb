# Design: union-same-kind-subset-filters

## Context

The **CandidateQuery** class (`backend/app/search/filter.py`) builds a lazy SQL `Select` from **SubsetFilter** predicates. Currently all subset predicates are appended to `WHERE` via a flat loop, composing them as AND (intersection). This is correct for cross-kind composition (datetime AND geo AND face), but wrong for same-kind composition: two datetime ranges (Jan-Mar, Jun-Aug) should be OR'd, not AND'd.

The **Filter** base class declares `kind: ClassVar[FilterKind]` on every filter subclass (ADR-0001), so grouping by `kind` is safe and straightforward. The existing architecture keeps all subset predicates in phase-1 and rank CTEs in phase-2 (ADR-0002); this change only affects how phase-1 predicates compose.

## Goals / Non-Goals

**Goals:**
- Same-kind subset filters compose via OR (union) before intersecting across kinds.
- Single-filter groups remain as direct `WHERE` predicates (no unnecessary OR wrapper).
- No changes to `SubsetFilter` interface, `RankFilter` composition, orchestrator, registry, or API contract.

**Non-Goals:**
- Configurable per-kind composition semantics (e.g., negation filters). Not needed today; future filter kinds can extend if required.
- Performance optimization for many same-kind filters. PostgreSQL handles linear OR chains efficiently; this is not a bottleneck.
- Changing the `SubsetFilter` or `Filter` class hierarchy. The grouping logic lives entirely in `CandidateQuery.__init__`.

## Decisions

### D1 — Group by `FilterKind`, compose intra-kind with `or_()`

**Choice**: In `CandidateQuery.__init__`, group `subset_filters` by `f.kind` into a `dict[FilterKind, list[SubsetFilter]]`. For each group: if single filter, append `build_predicate()` directly; if multiple, chain them with SQLAlchemy `or_()` and append the compound. Cross-group composition remains implicit AND via separate `WHERE` clauses.

**Alternatives considered**:
- **Explicit `and_()` across groups**: Unnecessary — multiple `WHERE` clauses already compose as AND in SQL.
- **Compose all into one compound predicate**: Overly complex; would need explicit `and_()` wrapping OR groups. Multiple `WHERE` clauses achieve the same result with simpler code.
- **Move grouping to orchestrator**: Changes `CandidateQuery` constructor signature and pushes grouping responsibility outside the class. Rejected — grouping is an implementation detail of `CandidateQuery`.

**Rationale**: SQLAlchemy's `or_()` wraps each group in parentheses via operator precedence, producing `(pred1 OR pred2) AND (pred3 OR pred4)` as intended. The flat `WHERE` clause approach is consistent with the existing code pattern.

### D2 — `FilterKind` as grouping key (not filter class)

**Choice**: Group by `f.kind` (the `FilterKind` enum value), not `type(f)`.

**Rationale**: Two different subclasses could share a `kind` (unlikely but possible); conversely, the same class might produce different predicates. The `kind` enum is the stable registry key (ADR-0001) and the persisted spec's identifier, so it's the correct semantic grouping dimension.

## Risks / Trade-offs

- [Semantic change for existing sessions] -> Sessions with multiple same-kind subset filters stored before this change will produce different (correct) results. This is a bug fix; no data migration needed — specs are unchanged, only reconstruction logic changes. Existing tests do not exercise multiple same-kind subset filters, so no test fixtures are affected.
- [OR chain length] -> If an agent adds many same-kind filters (e.g., 10 datetime ranges), the OR chain grows linearly. PostgreSQL handles this efficiently; not a practical concern at expected filter counts.
- [Future composition flexibility] -> Hardcoding same-kind = OR, cross-kind = AND. If a future filter kind needs different composition (e.g., negation), `CandidateQuery.__init__` would need extension. Not blocking — can be addressed when such a filter is designed.

## Migration Plan

- No database migration. Specs in JSONB are unchanged.
- No API change. Behavior is internal.
- Deploy and the new composition logic takes effect immediately for all sessions.
- Rollback = redeploy previous version. Worst case reverts to AND composition (the bug).

## Open Questions

- None. All in-force ADRs (0001-0004) remain coherent with this design. ADR-0001's "commutative WHERE clause" applies equally to OR composition.
