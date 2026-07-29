# Council Notes: proposal.md

## Author Summary
Proposal adds EXIF capture_time and geo columns to the image table, extracted during background processing. Uses strict timezone pairing and all-NULL GPS fallback. Stubs remain not-live.

## Reviewer Challenges
- Proposal lacks EXIF tag specificity (which offset tags map to which datetime tags?)
- No mention of delta spec file for modified capability
- No mention of tests
- No mention of API schema changes
- No rollback plan
- No logging strategy for EXIF failures

## Resolutions
Accepted: Author should specify exact EXIF tags for clarity and robustness
Accepted: Delta spec may be needed for modified capability
Accepted: Tests should be included
Accepted: API schema changes should be explicit
Accepted: Logging strategy should be documented

Rejected: No rollback plan needed for additive nullable columns

## Remaining Risks
- EXIF extraction performance on large images
- Validation of invalid GPS values
- Ambiguity in timezone offset tag selection