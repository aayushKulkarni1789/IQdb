# Council Notes: proposal.md

## Author Summary
Proposal for unioning same-kind SubsetFilters in CandidateQuery. Groups subset filters by kind, composes same-kind with OR, cross-kind with AND. Minimal change (~15 lines) to `CandidateQuery.__init__`. No interface changes, no API changes, no migrations.

## Reviewer Challenges
- Backward compatibility unaddressed: existing sessions with multiple same-kind subset filters will produce different results
- Test coverage: only 2 test functions mentioned, needs single-filter and mixed subset+rank cases
- Spec artifact needs MODIFIED requirement block with updated composition rule

## Resolutions
- Accepted: Added backward compatibility note (semantic bug fix, no migration needed)
- Accepted: Expanded test coverage to 3 functions (same-kind union, cross-kind intersection, mixed subset+rank)
- Accepted: Modified Capabilities correctly lists image-search as modified (reviewer may have misread original)

## Remaining Risks
- `f.kind` accessibility: verified safe — all SubsetFilter subclasses declare `kind` as ClassVar
- Performance with many same-kind filters: PostgreSQL handles linear OR chains fine, not blocking
