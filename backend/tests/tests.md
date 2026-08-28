# Test Cases

## `test_search.py` — 15 tests

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
| 12 | `test_unknown_kind_422_lists_valid_values` | Unknown filter kind returns 422 with error detail naming every valid kind; session still finalizes normally |
| 13 | `test_persisted_string_specs_round_trip` | `from_spec` creates a filter, `to_spec()` round-trips the original spec dict |
| 14 | `test_malformed_clip_spec_returns_structured_422` | Valid kind but missing required `text` returns 422 with structured detail (`Problems:`, `text`, `Expected format:`, `Example:`); bad spec not appended |
| 15 | `test_unknown_extra_fields_in_spec_are_ignored` | Unknown extra field in a valid spec is silently ignored, filter succeeds |

## `test_exif.py` — 26 tests

### `TestExtractCaptureTime` (16 tests)

| # | Test | What it does |
|---|---|---|
| 1 | `test_prefers_datetime_original` | DateTimeOriginal + offset → parsed datetime with timezone |
| 2 | `test_negative_offset` | DateTimeOriginal with `-08:00` → correct negative offset |
| 3 | `test_fallback_to_datetime_digitized` | No DateTimeOriginal, DateTimeDigitized present → fallback works |
| 4 | `test_prefers_original_over_digitized` | Both tags present → DateTimeOriginal preferred |
| 5 | `test_none_when_datetime_original_missing_offset` | DateTimeOriginal present but no offset → NULL |
| 6 | `test_none_when_no_datetime_tags` | No datetime tags → NULL |
| 7 | `test_none_when_no_exif` | No EXIF data → NULL |
| 8 | `test_none_when_no_exif_data_mock` | Empty EXIF → NULL |
| 9 | `test_none_when_datetime_digitized_missing_offset` | DateTimeDigitized present but no offset → NULL |
| 10 | `test_sub_ifd_tags_are_read` | Tags present only in the ExifIFD sub-IFD (`0x8769`) → parsed with sub-IFD offset |
| 11 | `test_sub_ifd_takes_precedence_over_top_level` | Same tag in both top-level and sub-IFD → sub-IFD value wins |
| 12 | `test_sub_ifd_offset_only` | Datetime in top-level, offset in sub-IFD → merged into a complete pair |
| 13 | `test_falls_through_to_digitized_when_original_incomplete` | DateTimeOriginal present but offset missing → falls through to DateTimeDigitized pair |
| 14 | `test_falls_through_when_original_datetime_unparseable` | DateTimeOriginal unparseable → falls through to DateTimeDigitized pair |
| 15 | `test_none_only_when_no_pair_complete` | Both pairs present but neither has an offset → NULL |
| 16 | `test_none_when_sub_ifd_original_unparseable_and_no_complete_pair` | sub-IFD datetime unparseable, no complete fallback → NULL |

### `TestExtractGps` (10 tests)

| # | Test | What it does |
|---|---|---|
| 17 | `test_valid_gps_coordinates` | GPS N/W with DMS → correct signed decimal degrees |
| 18 | `test_gps_dms_with_seconds` | GPS S/E with DMS including seconds → correct conversion |
| 19 | `test_none_when_gps_ifd_absent` | No GPS IFD → NULL |
| 20 | `test_none_when_no_exif` | No EXIF → NULL |
| 21 | `test_none_when_lat_missing` | Latitude tag absent → NULL |
| 22 | `test_none_when_lon_missing` | Longitude tag absent → NULL |
| 23 | `test_none_when_lat_out_of_bounds` | Latitude > 90 → NULL |
| 24 | `test_none_when_lon_out_of_bounds` | Longitude > 180 → NULL |
| 25 | `test_none_when_bounds_edge_cases` | Lat=90, Lon=180 → valid (boundary values pass) |
| 26 | `test_none_when_dms_tuple_invalid` | Invalid DMS format → NULL |

## `test_uploads.py` — 20 tests

### `TestStartUpload` (2 tests)

| # | Test | What it does |
|---|---|---|
| 1 | `test_start_upload` | Start upload with 10 images → 201, `"open"` status, job dir created |
| 2 | `test_start_upload_rejects_zero_count` | `expected_image_count=0` → 422 |

### `TestGetStatus` (2 tests)

| # | Test | What it does |
|---|---|---|
| 3 | `test_get_status` | GET status returns correct job_id, status, counts, and `created_at` |
| 4 | `test_get_status_404` | Nonexistent job ID → 404 |

### `TestBatchUpload` (6 tests)

| # | Test | What it does |
|---|---|---|
| 5 | `test_batch_single_image` | Upload 1 JPEG → 0 failures, file saved as `001_photo.jpg` |
| 6 | `test_batch_multiple_images` | Upload 3 images (JPEG, PNG, JPEG) → 0 failures, sequential filenames |
| 7 | `test_batch_rejects_non_image` | Upload `text/plain` → `failed=1`, `uploaded_count=0` |
| 8 | `test_batch_404_nonexistent_job` | Batch upload to nonexistent job → 404 |
| 9 | `test_batch_rejects_finalized_job` | Upload after job completion → 400 |
| 10 | `test_first_batch_transitions_to_uploading` | First batch upload transitions status from `"open"` to `"uploading"` |

### `TestResumeUpload` (1 test)

| # | Test | What it does |
|---|---|---|
| 11 | `test_resume_upload` | Two separate batches → `uploaded_count=2`, sequential prefixes |

### `TestCompleteUpload` (3 tests)

| # | Test | What it does |
|---|---|---|
| 12 | `test_complete_upload` | Upload all, complete → status goes `"uploaded"` → `"completed"` |
| 13 | `test_complete_rejects_count_mismatch` | Complete with 1/5 uploaded → 400 |
| 14 | `test_complete_rejects_open_job` | Complete with 0 uploads → 400 |

### `TestLargeBatch` (1 test)

| # | Test | What it does |
|---|---|---|
| 15 | `test_large_batch` | Upload `MAX_UPLOAD_BATCH_IMAGES` in one batch → 0 failures, correct count |

### `TestExifIngestion` (1 test)

| # | Test | What it does |
|---|---|---|
| 16 | `test_exif_data_stored_on_upload` | Upload EXIF-bearing JPEG, complete job → `capture_time`, `latitude`, `longitude` stored correctly (datetime tags read from the ExifIFD sub-IFD) |

### `TestCorruptBatchIngestion` (1 test)

| # | Test | What it does |
|---|---|---|
| 17 | `test_batch_with_corrupt_file_keeps_embeddings_aligned` | Batch containing one unopenable file → remaining valid images each receive the correct `capture_time` and the embedding computed from themselves; no embedding stored for the corrupt file |

### `TestIngestionSummary` (3 tests)

| # | Test | What it does |
|---|---|---|
| 18 | `test_successful_job_logs_full_summary` | Seed EXIF, plain, and corrupt files; monkey-patch embeddings; verify ingestion summary log contains `status=completed`, `total=3`, `opened_ok=2`, `written_to_db=2`, field counts, and `elapsed_seconds` |
| 19 | `test_grouped_fields_require_all_constituents` | Monkey-patch GPS to return `(40.5, None)` (missing longitude); verify `gps=0` in summary while `capture_time=1` still counted |
| 20 | `test_failed_job_logs_partial_summary` | Monkey-patch embeddings to raise; verify summary shows `status=failed`, `total=2`, `opened_ok=2`, `written_to_db=0`; job status set to `DISCARD` |
