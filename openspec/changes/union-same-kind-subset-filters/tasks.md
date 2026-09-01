## 1. Implement union-then-intersect composition

- [ ] 1.1 Modify `CandidateQuery.__init__` in `backend/app/search/filter.py` to group subset filters by `kind`, compose same-kind predicates with `or_()`, and compose cross-kind groups with `and_()`
- [ ] 1.2 Add import for `itertools.groupby` (or use `defaultdict`) and `sqlalchemy.or_` / `sqlalchemy.and_`

## 2. Tests

- [ ] 2.1 Add test: two same-kind subset filters produce OR composition (candidate count matches union)
- [ ] 2.2 Add test: cross-kind subset filters produce AND composition (candidate count matches intersection)
- [ ] 2.3 Add test: single subset filter still works (no regression)
- [ ] 2.4 Add test: mixed subset + rank filter composition (union doesn't break phase-2 RRF)
- [ ] 2.5 Run `make test` to verify all tests pass

## 3. Validate and archive

- [ ] 3.1 Run `openspec validate union-same-kind-subset-filters --type change --strict`
- [ ] 3.2 Run `openspec archive union-same-kind-subset-filters`
