# Council Notes: proposal

## Author Summary
Proposal for change `fix-capture-time-and-ingestion-memory`. Root causes: (1) `extract_capture_time()` reads EXIF only from the top-level 0th IFD while real camera files store datetime/offset tags in the ExifIFD sub-IFD (`0x8769`) — verified 160/167 sample images carry all four tags there and none at top level; (2) ingestion keeps the whole CLIP batch of decoded images resident through the per-image metadata loop, driving peak RAM to ~99%. The change fixes the IFD lookup and fallback loop, closes batch images right after CLIP inference, corrects a latent file/embedding misalignment bug, and updates tests so the integration test writes tags into the sub-IFD. Strict NULL rule kept (no naive/UTC fallback). Batch size default unchanged.

## Reviewer Challenges
- **Blocking:** The latent zip-misalignment bug (pairing `batch_files` with shorter `embeddings` when `PILImage.open()` fails) was missing from What Changes and Impact; without it the tasks phase cannot cover a user-decided in-scope fix.
- The phrase "halves peak memory" overclaims; no measurement supports a fixed 50% reduction.
- The sibling change `exif-capture-time-and-geo` (unarchived at review time) also targets the `image-search` spec and adds the `capture_time`/`latitude`/`longitude` columns; without acknowledgment the spec delta could drift or contradict.
- Why section was a single dense paragraph; improve scanability.
- Memory fix should name the exact late-close loop being removed.
- Capabilities wording should confirm pair priority (`DateTimeOriginal` before `DateTimeDigitized`) is preserved.
- Zip-misalignment needs a test that injects a corrupt file into a batch.

## Resolutions
- Accepted: zip-misalignment fix added to What Changes and Impact, plus a corrupt-file batch test.
- Accepted: removed any percentage memory claim; now "reduces peak memory by releasing decoded pixels earlier".
- Accepted: added explicit dependency note on the `exif-capture-time-and-geo` change (now archived).
- Accepted: Why tightened into separate sentences; late-close loop described explicitly; pair priority made explicit.
- The reviewer's draft quote still contained "halves peak memory", but the author draft had already dropped it; final artifact contains no such claim.

## Remaining Risks
- Spec delta for `image-search` was authored against the post-merge state of the archived `exif-capture-time-and-geo` change (archived 2026-08-03); the two deltas are coherent.
- The zip-misalignment fix is only exercised when a file fails to open mid-batch; the new corrupt-file test mitigates regression risk.
