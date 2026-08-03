# Fix Capture Time and Ingestion Memory

## Why

`capture_time` is `NULL` for every one of the user's 150+ real photos. `extract_capture_time()` reads EXIF only from the top-level 0th IFD, but cameras and phones store `DateTimeOriginal`/`OffsetTimeOriginal` and `DateTimeDigitized`/`OffsetTimeDigitized` inside the ExifIFD sub-IFD (`0x8769`). Verified against 167 real photos in `./output`: 160 carry all four tags in the sub-IFD, none at the top level. `extract_gps()` already reads its own sub-IFD (`0x8825`) and works — which is why only `capture_time` fails.

Ingestion also decodes an entire CLIP batch of ~12MP images at once, then keeps the decoded images resident through the per-image metadata loop (which re-opens every file) and the DB writes, driving peak RAM to ~99%. Metadata extraction is header-only and never needs decoded pixels, so holding the batch open through those phases is pure waste.

This change depends on the archived `exif-capture-time-and-geo` change, which adds the `capture_time`, `latitude`, and `longitude` columns; this fix corrects the EXIF extraction logic so those columns are actually populated.

## What Changes

- `extract_capture_time()` reads datetime/offset tags from the ExifIFD sub-IFD (`0x8769`) in addition to the top-level 0th IFD, with sub-IFD values taking precedence — the same pattern `extract_gps()` already uses for the GPS IFD. Pair priority is preserved: `DateTimeOriginal` is preferred over `DateTimeDigitized`.
- The datetime-pair fallback is corrected: when a tag pair is incomplete (datetime unparseable, offset missing, or offset unparseable), extraction falls through to the next pair instead of returning `NULL`. The strict rule is preserved: `capture_time` is `NULL` only when no (datetime, offset) pair is complete; no naive/UTC fallback is introduced.
- `process_upload_embeddings()` extracts metadata (size, EXIF, GPS) from each image's lazy-open handle before inference — a header-only operation that never decodes pixels and never re-reads the file — then runs CLIP inference on the batch, closes every handle immediately after inference returns, and performs DB writes with decoded pixels already released. The per-file re-open for metadata and the late close loop after `db.commit()` are removed. The `MAX_CLIP_BATCH_IMAGES` default is unchanged; the inference-time decode footprint is inherent to batching full-res images and is not changed.
- The per-batch file/embedding pairing is corrected: only files that were successfully opened are paired with their corresponding embeddings, preventing positional misalignment when `PILImage.open()` fails for any file in the batch (previously an embedding could be stored against the wrong image).
- Tests: `test_exif.py` gains unit tests for sub-IFD lookup and the corrected fallback; `test_uploads.py`'s `_make_exif_image_file()` writes datetime tags into the ExifIFD sub-IFD via `exif.get_ifd(0x8769)` so the integration test mirrors real camera output (today it writes top-level tags, which is why the bug passed CI). A test is added covering a batch containing a corrupt file, verifying remaining files receive correct embeddings.

No breaking changes: no migrations, no API surface changes, no dependency changes.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `image-search`: EXIF datetime/offset extraction during ingestion must locate tags in the ExifIFD sub-IFD (`0x8769`) as well as the top-level IFD, so `capture_time` is populated for real camera/phone files; fallback to `DateTimeDigitized` must be attempted when `DateTimeOriginal` is present but incomplete.

## Impact

- `backend/app/search/exif.py` — `extract_capture_time()` reads the ExifIFD sub-IFD and falls through to the next (datetime, offset) pair when a pair is incomplete.
- `backend/app/tasks.py` — `process_upload_embeddings()` extracts metadata from each lazy-open handle before inference, closes batch handles immediately after inference, and pairs embeddings with successfully-opened files.
- `backend/tests/test_exif.py` — new unit tests for sub-IFD lookup and fallback behavior.
- `backend/tests/test_uploads.py` — `_make_exif_image_file()` writes datetime tags into the ExifIFD sub-IFD; a corrupt-file batch test covers the embedding-pairing fix.
- No migrations, no API changes, no new dependencies.
