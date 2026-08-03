# Tasks: Fix Capture Time and Ingestion Memory

## 1. Fix EXIF capture time extraction

- [ ] 1.1 Modify `extract_capture_time()` in `backend/app/search/exif.py` to read datetime/offset tags from the ExifIFD sub-IFD (`0x8769`) via `exif_data.get_ifd(0x8769)` in addition to the top-level 0th IFD, with sub-IFD values taking precedence (same pattern as `extract_gps()`).
- [ ] 1.2 Replace the three `return None` branches in the fallback loop (datetime unparseable, offset tag missing, offset unparseable) with `continue`, preserving the `DateTimeOriginal` over `DateTimeDigitized` preference and the strict rule that `capture_time` is `NULL` only when no (datetime, offset) pair is complete.

## 2. Fix ingestion memory and embedding pairing

- [ ] 2.1 In `process_upload_embeddings()` (`backend/app/tasks.py`), close every image in `pil_images` immediately after `get_image_embeddings(pil_images)` returns and remove the late close loop after `db.commit()`. Do not change the `MAX_CLIP_BATCH_IMAGES` default.
- [ ] 2.2 In the per-batch loop, pair embeddings with only the files that were successfully opened into `pil_images`, so a file that fails `PILImage.open()` does not shift embeddings onto the wrong image.

## 3. Update tests

- [ ] 3.1 Extend the mock helper in `backend/tests/test_exif.py` to model `get_ifd(0x8769)` (ExifIFD sub-IFD) and add unit tests: sub-IFD tags are read; sub-IFD takes precedence over top-level; fallback to `DateTimeDigitized` when `DateTimeOriginal` is incomplete; `NULL` only when no pair is complete.
- [ ] 3.2 Change `_make_exif_image_file()` in `backend/tests/test_uploads.py` to write `DateTimeOriginal`/`OffsetTimeOriginal`/`DateTimeDigitized`/`OffsetTimeDigitized` into the ExifIFD sub-IFD via `exif.get_ifd(0x8769)` (mirroring real camera output), keeping GPS in the GPS IFD.
- [ ] 3.3 Add a batch test to `backend/tests/test_uploads.py` containing one corrupt file, asserting the remaining images receive the correct embeddings and `capture_time`.

## 4. Verify

- [ ] 4.1 Start services with `docker compose up -d` and run `make test`; all tests pass.
- [ ] 4.2 Run `openspec validate fix-capture-time-and-ingestion-memory --type change --strict` and confirm the change is valid.
