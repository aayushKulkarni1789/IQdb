# Test Cases

## `test_search.py` — 11 tests

| # | Test | What it does |
|---|---|---|
| 1 | `test_create_session` | POST to `/sessions` creates a session with an integer ID |
| 2 | `test_apply_filters_in_any_order` | Two consecutive CLIP filter apps on same session both succeed |
| 3 | `test_finalize_returns_top_k` | Seeds 10 images, finalizes with `top_k=10`, checks response shape; second finalize returns 409 |
| 4 | `test_finalized_session_rejects_ops` | After finalizing, new filter or re-finalize both return 409 |
| 5 | `test_candidate_count_excludes_rank_filters` | CLIP filter candidate count equals total seeded images (rank filters don't reduce pool) |
| 6 | `test_rrf_skipped_when_no_rank_filters` | No rank filters → all scores are `None`, results in ascending ID order |
| 7 | `test_clip_rank_end_to_end` | Monkey-patches CLIP encoder, seeds images, asserts best match has highest score |
| 8 | `test_stub_filter_rejected_at_add_time` | Unimplemented `"datetime"` filter returns 501, but session can still finalize |
| 9 | `test_registry_advertises_liveness` | CLIP is `live=True`; `datetime`, `geo`, `face` are `live=False` |
| 10 | `test_unknown_filter_kind_returns_422` | Unknown filter kind returns 422; session remains usable, finalize returns all images |
| 11 | `test_two_phase_execution_with_mixed_filters` | Unit test of `CandidateQuery` with inline mock subset+rank filters; verifies RRF scores, all images returned, construction order independence |

## `test_uploads.py` — 15 tests

### `TestStartUpload` (2 tests)

| # | Test | What it does |
|---|---|---|
| 10 | `test_start_upload` | Start upload with 10 images → 201, `"open"` status, job dir created |
| 11 | `test_start_upload_rejects_zero_count` | `expected_image_count=0` → 422 |

### `TestGetStatus` (2 tests)

| # | Test | What it does |
|---|---|---|
| 12 | `test_get_status` | GET status returns correct job_id, status, counts, and `created_at` |
| 13 | `test_get_status_404` | Nonexistent job ID → 404 |

### `TestBatchUpload` (6 tests)

| # | Test | What it does |
|---|---|---|
| 14 | `test_batch_single_image` | Upload 1 JPEG → 0 failures, file saved as `001_photo.jpg` |
| 15 | `test_batch_multiple_images` | Upload 3 images (JPEG, PNG, JPEG) → 0 failures, sequential filenames |
| 16 | `test_batch_rejects_non_image` | Upload `text/plain` → `failed=1`, `uploaded_count=0` |
| 17 | `test_batch_404_nonexistent_job` | Batch upload to nonexistent job → 404 |
| 18 | `test_batch_rejects_finalized_job` | Upload after job completion → 400 |
| 19 | `test_first_batch_transitions_to_uploading` | First batch upload transitions status from `"open"` to `"uploading"` |

### `TestResumeUpload` (1 test)

| # | Test | What it does |
|---|---|---|
| 20 | `test_resume_upload` | Two separate batches → `uploaded_count=2`, sequential prefixes |

### `TestCompleteUpload` (3 tests)

| # | Test | What it does |
|---|---|---|
| 21 | `test_complete_upload` | Upload all, complete → status goes `"uploaded"` → `"completed"` |
| 22 | `test_complete_rejects_count_mismatch` | Complete with 1/5 uploaded → 400 |
| 23 | `test_complete_rejects_open_job` | Complete with 0 uploads → 400 |

### `TestLargeBatch` (1 test)

| # | Test | What it does |
|---|---|---|
| 24 | `test_large_batch` | Upload `MAX_UPLOAD_BATCH_IMAGES` in one batch → 0 failures, correct count |
