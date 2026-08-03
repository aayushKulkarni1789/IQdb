# Fix Capture Time and Ingestion Memory

## Why

`capture_time` is `NULL` for every one of the user's 150+ real photos. `extract_capture_time()` reads EXIF only from the top-level 0th IFD, but cameras and phones store `DateTimeOriginal`/`OffsetTimeOriginal` and `DateTimeDigitized`/`OffsetTimeDigitized` inside the ExifIFD sub-IFD (`0x8769`). Verified against 167 real photos in `./output`: 160 carry all four tags in the sub-IFD, none at the top level. `extract_gps()` already reads its own sub-IFD (`0x8825`) and works — which is why only `capture_time` fails.

Ingestion also holds every decoded image in a CLIP batch in memory through the whole per-image metadata loop, driving peak RAM to ~99% on ~12MP photos.

This change depends on the unarchived `exif-capture-time-and-geo` change, which adds the `capture_time`, `latitude`, and `longitude` columns; this fix corrects the EXIF extraction logic so those columns are actually populated.

## What Changes

- `extract_capture_time()` reads datetime/offset tags from the ExifIFD sub-IFD (`0x8769`) in addition to the top-level 0th IFD, with sub-IFD values taking precedence — the same pattern `extract_gps()` already uses for the GPS IFD. Pair priority is preserved: `DateTimeOriginal` is preferred over `DateTimeDigitized`.
- The datetime-pair fallback is corrected: when a tag pair is incomplete (datetime unparseable, offset missing, or offset unparseable), extraction falls through to the next pair instead of returning `NULL`. The strict rule is preserved: `capture_time` is `NULL` only when no (datetime, offset) pair is complete; no naive/UTC fallback is introduced.
- `process_upload_embeddings()` closes the CLIP batch's PIL images immediately after `get_image_embeddings()` returns, before per-image metadata extraction begins (which reopens its own handles); the redundant late close loop after `db.commit()` is removed. This reduces peak memory by releasing decoded pixels earlier so batch images and metadata images are not simultaneously resident. The `MAX_CLIP_BATCH_IMAGES` default is unchanged.
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
- `backend/app/tasks.py` — `process_upload_embeddings()` releases CLIP batch images right after embedding inference, removes the late close loop, and pairs files with embeddings using only successfully-opened files.
- `backend/tests/test_exif.py` — new unit tests for sub-IFD lookup and fallback behavior.
- `backend/tests/test_uploads.py` — `_make_exif_image_file()` writes datetime tags into the ExifIFD sub-IFD; a corrupt-file batch test covers the embedding-pairing fix.
- No migrations, no API changes, no new dependencies.
