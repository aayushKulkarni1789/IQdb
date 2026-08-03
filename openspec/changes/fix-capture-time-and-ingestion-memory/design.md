# Design: Fix Capture Time and Ingestion Memory

## Context

The **Image Search** capability ingests uploads through `backend/app/tasks.py:process_upload_embeddings`, which extracts EXIF metadata (`capture_time`, `latitude`, `longitude`) for every image. Two defects are confirmed against 167 real photos in `./output`:

1. `extract_capture_time()` in `backend/app/search/exif.py` reads EXIF datetime/offset tags only from the top-level 0th IFD. Cameras and phones store `DateTimeOriginal` (0x9003), `OffsetTimeOriginal` (0x9011), `DateTimeDigitized` (0x9004), and `OffsetTimeDigitized` (0x9012) inside the ExifIFD sub-IFD (`0x8769`). Measured: 160/167 images carry all four tags in the sub-IFD, none at the top level. `extract_gps()` already reads its own GPS sub-IFD (`0x8825`) and works, which is why only `capture_time` is always `NULL`. The existing integration test passes because its synthetic image writes tags to the top level, unlike real cameras.
2. The pipeline decodes the entire CLIP batch of full-res pixels during inference, then keeps those decoded images resident through the per-image metadata loop — which re-opens every file — and the DB writes, closing them only after `db.commit()`. At `MAX_CLIP_BATCH_IMAGES=100` on ~12MP photos this drives peak RAM to ~99%. Metadata extraction is header-only (size and EXIF come from the file header, never the decoded pixels), so holding decoded images through that phase is pure waste, and the per-file re-open duplicates the read.

Additionally, the per-batch loop `for f, embedding in zip(batch_files, embeddings)` misaligns files and embeddings if `PILImage.open(f)` fails for any file: the failed file is skipped from `pil_images`, `embeddings` is shorter, and positional `zip` stores each embedding against the wrong image.

## Goals / Non-Goals

**Goals:**
- Populate `capture_time` for real camera/phone files by reading the ExifIFD sub-IFD (`0x8769`) in addition to the top-level IFD, with sub-IFD values taking precedence.
- Preserve strict tagging: `capture_time` is `NULL` only when no (datetime, offset) pair is complete.
- Extract metadata from each lazy-open handle before inference (header-only, no pixel decode, no re-read) and close every batch handle immediately after inference so DB writes run at near-zero memory.
- Pair embeddings with the files that actually produced them, preventing wrong-image embeddings.
- Update tests so the integration test mirrors real camera output and unit tests cover the new paths.

**Non-Goals:**
- Changing the `MAX_CLIP_BATCH_IMAGES` default.
- Relaxing strict pairing with a naive/UTC fallback.
- Backfilling existing images.
- Changing the API surface, database schema, or dependencies.

## Decisions

### 1. Read datetime tags from the ExifIFd sub-IFD with precedence

**Decision:** `extract_capture_time()` reads the ExifIFD sub-IFD (`0x8769`) via `exif_data.get_ifd(0x8769)` in addition to the top-level IFD, using the same pattern `extract_gps()` already applies to the GPS IFD (`0x8825`). Sub-IFD values take precedence over top-level values.

**Why:** Real camera/phone files place datetime tags in the sub-IFD. Reading both IFDs with sub-IFD precedence fixes production while remaining backward-compatible with any file that stores tags at the top level.

**Alternatives considered:**
- Rely on Pillow's `get_exif()` re-parsing: `getexif()` already exposes the sub-IFD via `get_ifd`; re-parsing raw bytes adds complexity.
- Search all IFDs depth-first: Overkill for two known IFD levels and changes precedence semantics.

### 2. Fall through to the next datetime pair instead of aborting

**Decision:** Replace the three `return None` branches in the fallback loop (datetime unparseable, offset tag missing, offset unparseable) with `continue`. The loop still prefers `DateTimeOriginal` + `OffsetTimeOriginal`, then `DateTimeDigitized` + `OffsetTimeDigitized`; `capture_time` is `NULL` only when neither pair is complete.

**Why:** A present-but-incomplete or unparseable `DateTimeOriginal` should not discard a valid `DateTimeDigitized` pair. This makes the fallback behave as the original design intended while preserving the strict NULL rule.

**Alternatives considered:**
- Keep abort-on-incomplete: Defeats the fallback when `DateTimeOriginal` exists but is unusable.
- Add a naive-datetime fallback: Rejected by requirement; ambiguous datetimes are worse than `NULL`.

### 3. Extract metadata from the lazy handle, close immediately after inference

**Decision:** In `process_upload_embeddings()`, after opening each file, extract metadata (`img.size`, `extract_capture_time`, `extract_gps`) from the same lazy-open handle — a header/EXIF-only operation that never decodes pixels and requires no additional read — before calling `get_image_embeddings(pil_images)`. Immediately after inference returns, call `img.close()` for every image in `pil_images`. Remove both the per-file re-open (`with PILImage.open(f)`) in the metadata phase and the late close loop after `db.commit()`.

**Why:** `PILImage.open()` is lazy: `size` and EXIF come from the file header, so metadata never needs decoded pixels and never re-reads the file. Decoded pixels are only required by the inference call, and are freed the moment it returns, so the DB-write loop runs at near-zero memory. The decode spike during inference is inherent to batching full-res images and is intentionally unchanged.

**Alternatives considered:**
- Keep the late close (current behavior): decoded images stay resident through the metadata re-open and DB writes, causing ~99% peak RAM.
- Close after inference and re-open for metadata (original proposal): releases memory but re-reads the file; the second read is redundant.
- Downscale before embedding: changes model input behavior; out of scope.

### 4. Pair embeddings only with successfully-opened files

**Decision:** Collect a metadata tuple per successfully-opened image alongside `pil_images` (the same list whose order produces `embeddings`), and zip that metadata with `embeddings` — never the raw `batch_files` list.

**Why:** Positional `zip(batch_files, embeddings)` silently misaligns when a file fails to open — the failed file is absent from `pil_images`, so embeddings shift and are stored against the wrong images. Since metadata and embeddings are both derived from the single `pil_images` success list, zipping them is trivially aligned and guarantees each embedding is stored with the image that generated it.

**Alternatives considered:**
- Raise on any open failure: Would abort the whole batch on one corrupt file; the pipeline is designed to degrade gracefully (per-image failures produce `NULL` metadata, not ingestion failure).

### 5. Tests mirror real camera EXIF layout

**Decision:** Update `backend/tests/test_uploads.py:_make_exif_image_file` to write datetime/offset tags into the ExifIFd sub-IFD via `exif.get_ifd(0x8769)` (matching real camera output), and extend `backend/tests/test_exif.py`'s mock helper to model `get_ifd(0x8769)`. Add a corrupt-file batch test to exercise the embedding-pairing fix.

**Why:** The prior integration test wrote tags to the top level, so it could not catch the sub-IFD bug — exactly why the defect shipped despite green tests.

## Risks / Trade-offs

- **[Risk] Sub-IFD precedence changes `capture_time` for files that have both top-level and sub-IFD datetime tags** -> Mitigation: Sub-IFD is where real cameras write authoritative tags; behavior is verified by the new unit and integration tests.
- **[Risk] Closing images right after inference could break if metadata extraction depends on the open handle** -> Mitigation: Metadata is extracted from the same lazy handle *before* inference, so nothing touches `pil_images` after they are closed.
- **[Risk] Embedding-pairing fix is only exercised when a file fails to open** -> Mitigation: New corrupt-file batch test covers the regression.
- **[Trade-off] A photo with `DateTimeOriginal` but no offset and a complete `DateTimeDigitized` pair now produces a time instead of `NULL`** -> Mitigation: This is the explicit fall-through requirement; it favors usable data over strict abandonment.

## Migration Plan

1. Modify `backend/app/search/exif.py` (sub-IFD lookup, fall-through loop).
2. Modify `backend/app/tasks.py` (metadata-from-lazy-handle, early close, pairing fix).
3. Update unit and integration tests.
4. Run `docker compose up -d` and `make test`; all tests must pass.

No database migration, API change, or dependency change. Rollback is a code revert of the two modules and tests; existing rows are unaffected (columns already exist from the archived `exif-capture-time-and-geo` change).

## Open Questions

- None. In-force ADRs (`0001-filter-subset-rank-taxonomy`, `0002-lazy-sql-pushdown-candidatequery`, `0003-reciprocal-rank-fusion`) constrain the search pipeline only and are unaffected by ingestion-time EXIF extraction and batch memory handling.
