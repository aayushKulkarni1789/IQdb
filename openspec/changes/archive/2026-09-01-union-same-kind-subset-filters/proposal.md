# Proposal: union-same-kind-subset-filters

## Why

Currently all `SubsetFilter` predicates are composed via AND (intersection) in `CandidateQuery.__init__`. This means if an agent adds two datetime filters — e.g., "images from Jan-Mar" and "images from Jun-Aug" — they intersect to zero results because no image can satisfy both ranges simultaneously. The natural semantics for same-kind subset filters is union (OR): "show me images from Jan-Mar **or** Jun-Aug." Cross-kind composition remains intersect (AND).

## What Changes

- Modify `CandidateQuery.__init__` to group subset filters by `kind` before composing predicates: same-kind filters compose via OR (union), cross-kind filters compose via AND (intersect).
- Single-filter groups are unchanged (no unnecessary OR wrapper).
- No changes to `SubsetFilter` interface, `RankFilter` composition (RRF), orchestrator, registry, filter implementations, or API contract.
- This is a semantic bug fix: existing sessions with multiple same-kind subset filters will produce different (correct) results. No data migration needed — specs are unchanged, only reconstruction logic changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `image-search`: subset filters of the same kind are now unioned (OR) before intersecting across kinds. Previously all subset predicates were intersected (AND). The SQL `WHERE` clause changes from `pred1 AND pred2 AND pred3` to `(pred_dt1 OR pred_dt2) AND (pred_geo1 OR pred_geo2)`.

## Impact

- **Code**: `backend/app/search/filter.py` — `CandidateQuery.__init__` (lines 109-118), ~15 lines changed
- **Tests**: `backend/tests/test_search.py` — 3 new test functions: same-kind union (disjoint predicates), cross-kind intersection (AND across kinds), and mixed subset+rank composition to verify union doesn't interfere with phase-2 RRF
- **APIs**: No changes. The behavior change is internal; same inputs, different (correct) results when multiple same-kind subset filters are present
- **Database**: No migrations. Specs stored in JSONB are unchanged; grouping happens at reconstruct time
- **Specs**: modifies the existing `image-search` spec to document the union-then-intersect composition rule
