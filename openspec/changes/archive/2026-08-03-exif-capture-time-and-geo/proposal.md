# EXIF Capture Time and Geo Ingestion

## Why

The image ingestion pipeline currently stores only `uploaded_at` as a temporal reference, which reflects when the file was uploaded — not when the photo was actually taken. Similarly, no geographic location is stored. The `DatetimeFilter` and `GeoFilter` stubs already exist in the search framework but are marked `is_live = false` because the underlying data was never ingested. This change fills that gap by extracting EXIF metadata during the existing background processing step, enabling future filter implementations to query by capture time and location.

## What Changes

- Add three nullable columns to the `image` table: `capture_time` (TIMESTAMPTZ), `latitude` (DOUBLE PRECISION), `longitude` (DOUBLE PRECISION)
- Expose `capture_time`, `latitude`, `longitude` in the `ImagePublic` API response schema
- Extract EXIF datetime with strict tag pairing:
  - `DateTimeOriginal` (0x9003) + `OffsetTimeOriginal` (0x9011) → preferred
  - `DateTimeDigitized` (0x9004) + `OffsetTimeDigitized` (0x9012) → fallback
  - If the chosen datetime tag is present but its matching offset tag is missing → `capture_time = NULL`
  - If neither datetime tag is present → `capture_time = NULL`
- Extract GPS latitude/longitude from EXIF GPS IFD; store as signed decimal degrees with validation (lat: [-90, 90], lon: [-180, 180]); store both as NULL if either is absent or out of bounds
- Log EXIF extraction outcomes at DEBUG level; log failures and invalid data at WARNING level
- Move `pillow` from `model-setup` dependency group to main `dependencies` (fixes implicit runtime dependency)

## Non-Goals

- Backfilling `capture_time` for existing images (new columns are NULL for existing rows)
- Implementing `DatetimeFilter` or `GeoFilter` query logic (stubs remain not-live)
- Updating `GeoFilter` stub error messages to reflect new columns

## Capabilities

- **Modified Capabilities**:
  - `image-search` — The image data model gains `capture_time`, `latitude`, `longitude` columns; the ingestion pipeline extracts and stores EXIF metadata; the existing `DatetimeFilter` and `GeoFilter` stubs remain as-is (filter implementation is deferred)

## Impact

- `backend/app/models.py` — `Image` table and `ImagePublic` schema gain 3 fields
- `backend/app/crud.py` — `create_image()` accepts new parameters
- `backend/app/tasks.py` — EXIF extraction logic added to `process_upload_embeddings()`
- `backend/app/alembic/versions/` — New migration for 3 nullable columns
- `backend/pyproject.toml` — `pillow` moved to main dependencies (bugfix: already imported at runtime)
- `backend/tests/` — Unit tests for EXIF extraction utilities and integration test for ingestion with EXIF-bearing images
