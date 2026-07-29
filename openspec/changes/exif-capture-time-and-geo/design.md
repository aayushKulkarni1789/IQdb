# Design: EXIF Capture Time and Geo Ingestion

## Context

The image ingestion pipeline (`backend/app/tasks.py:process_upload_embeddings`) currently opens images only for CLIP embedding extraction. The `Image` table (`backend/app/models.py:Image`) stores `uploaded_at` but not when the photo was actually taken, and has no geographic data. The `DatetimeFilter` and `GeoFilter` stubs exist but are non-functional because the underlying columns do not exist.

This design adds EXIF metadata extraction during the existing background processing step, populating three new nullable columns: `capture_time`, `latitude`, `longitude`.

## Goals / Non-Goals

**Goals:**
- Extract EXIF datetime with strict tag pairing (datetime + offset must both be present)
- Extract GPS coordinates as signed decimal degrees with validation
- Keep extraction logic isolated in utility functions for testability
- Preserve existing pipeline behavior; new fields are optional/nullable

**Non-Goals:**
- Backfilling existing images
- Implementing filter query logic (stubs remain non-live)
- Supporting non-EXIF metadata sources (XMP, IPTC)

## Decisions

### 1. EXIF extraction via Pillow's `getexif()` API

**Decision:** Use `PIL.Image.getexif()` to read IFD tags directly by numeric ID.

**Why:** Pillow is already a runtime dependency (used in `tasks.py`). The EXIF API provides direct access to the specific tags needed:
- `0x9003` (DateTimeOriginal), `0x9011` (OffsetTimeOriginal)
- `0x9004` (DateTimeDigitized), `0x9012` (OffsetTimeDigitized)
- GPS IFD (`0x8825`) for latitude/longitude

**Alternatives considered:**
- `exifread` library: Adds a dependency; Pillow's API is sufficient for the required tags.
- `piexif`: Operates on raw EXIF bytes; more complex for read-only extraction.

### 2. Strict datetime tag pairing

**Decision:** Require both datetime and its matching offset tag to produce a `capture_time`. If the datetime tag is present but the offset tag is missing, store `NULL`.

**Why:** A datetime without timezone offset is ambiguous. The proposal explicitly specifies this behavior. The pairing rules are:
- Prefer `DateTimeOriginal` + `OffsetTimeOriginal`
- Fall back to `DateTimeDigitized` + `OffsetTimeDigitized`
- Parse datetime string (`%Y:%m:%d %H:%M:%S`) then apply offset to produce `TIMESTAMPTZ`

**Alternatives considered:**
- Store naive datetime and assume UTC: Loses timezone information; incorrect for photos taken in non-UTC zones.
- Store datetime string as-is: Defers parsing to query time; complicates filtering.

### 3. GPS coordinate extraction and validation

**Decision:** Extract from GPS IFD; convert DMS rational tuples to signed decimal degrees; validate bounds (lat: [-90, 90], lon: [-180, 180]); store both as `NULL` if either is absent or invalid.

**Why:** Decimal degrees are the standard for postGIS/spatial queries. Storing both as NULL when either is missing prevents partial/meaningless coordinates. The GPS IFD contains:
- `0x0001` (GPSLatitudeRef), `0x0002` (GPSLatitude)
- `0x0003` (GPSLongitudeRef), `0x0004` (GPSLongitude)

Latitude/longitude are stored as rational triplets (degrees, minutes, seconds) that must be converted to float.

### 4. Extraction as module-level utility functions under `backend/app/search/`

**Decision:** Place EXIF extraction in a new `backend/app/search/exif.py` module with two public functions: `extract_capture_time(img: PILImage.Image) -> datetime | None` and `extract_gps(img: PILImage.Image) -> tuple[float, float] | None`.

**Why:** EXIF extraction is part of the image search capability — `capture_time` and geo fields are consumed by `DatetimeFilter` and `GeoFilter` in the search pipeline. Co-locating with the filter stubs (`backend/app/search/`) keeps related functionality together under the same package. Isolating extraction logic in a dedicated module enables unit testing without running the full ingestion pipeline, and keeps `tasks.py` focused on orchestration.

**Alternatives considered:**
- `backend/app/exif.py`: Still viable but places extraction outside the search package, separating it from its consuming filters.
- Inline in `tasks.py`: Simpler but harder to test; violates single-responsibility.
- Separate microservice: Over-engineered for a synchronous extraction step.

### 5. Alembic migration: add three nullable columns

**Decision:** Single migration adding `capture_time TIMESTAMPTZ NULL`, `latitude DOUBLE PRECISION NULL`, `longitude DOUBLE PRECISION NULL` to the `image` table.

**Why:** Nullable columns require no default value and do not lock the table for existing rows. No data backfill needed.

### 6. Move `pillow` to main dependencies

**Decision:** Move `pillow` from `[dependency-groups] model-setup` to `[project.dependencies]` in `pyproject.toml`.

**Why:** Pillow is imported at runtime in `tasks.py` and will be used in `exif.py`. It should be a declared runtime dependency, not a dev/setup dependency.

## Risks / Trade-offs

- **[Risk] EXIF data may be absent or corrupted in many image formats** -> Mitigation: All extraction failures result in `NULL` fields; no ingestion failure. Logged at WARNING level.
- **[Risk] GPS IFD parsing edge cases (e.g., missing ref tags, zero-valued coordinates)** -> Mitigation: Validate coordinate bounds; store `NULL` on any inconsistency.
- **[Trade-off] Strict datetime pairing rejects photos with datetime but no offset** -> Mitigation: This is the explicit requirement; ambiguous datetimes are worse than missing data.

## Migration Plan

1. Create `backend/app/search/exif.py` with extraction utilities
2. Add unit tests for extraction functions
3. Add `capture_time`, `latitude`, `longitude` columns via Alembic migration
4. Update `Image` model and `ImagePublic` schema
5. Update `create_image()` in `crud.py` to accept new parameters
6. Update `process_upload_embeddings()` in `tasks.py` to call extraction and pass values
7. Move `pillow` to main dependencies in `pyproject.toml`
8. Add integration test for ingestion with EXIF-bearing images

Rollback: Reverse Alembic migration (drops nullable columns; no data loss for existing rows).

## Open Questions

- None. All in-force ADRs (0001, 0002, 0003) are compatible with this design; this change does not affect the search/filter pipeline or CandidateQuery.
