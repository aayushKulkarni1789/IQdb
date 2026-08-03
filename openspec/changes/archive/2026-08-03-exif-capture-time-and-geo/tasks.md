## 1. Dependency Setup

- [x] 1.1 Move `pillow` from `[dependency-groups.model-setup]` to `[project.dependencies]` in `backend/pyproject.toml`

## 2. EXIF Extraction Module

- [x] 2.2 Create `backend/app/search/exif.py` with `extract_capture_time(img: Image.Image) -> datetime | None` and `extract_gps(img: Image.Image) -> tuple[float, float] | None`
- [x] 2.3 Write unit tests for EXIF extraction in `backend/tests/test_exif.py` covering tag pairing, fallback, missing tags, GPS DMS conversion, and bounds validation

## 3. Schema and Model

- [x] 3.1 Generate Alembic migration with `make migrate msg="add capture_time latitude longitude to image"` and apply with `make upgrade` to add `capture_time TIMESTAMPTZ`, `latitude DOUBLE PRECISION`, `longitude DOUBLE PRECISION` (all nullable) to `image` table
- [x] 3.2 Add `capture_time`, `latitude`, `longitude` fields to `Image` model and `ImagePublic` schema in `backend/app/models.py`

## 4. Ingestion Pipeline

- [x] 4.1 Update `create_image()` in `backend/app/crud.py` to accept `capture_time`, `latitude`, `longitude` parameters
- [x] 4.2 Update `process_upload_embeddings()` in `backend/app/tasks.py` to call EXIF extraction and pass values to `create_image()`

## 5. Testing and Validation

- [x] 5.1 Add integration test in `backend/tests/test_uploads.py` for ingestion with an EXIF-bearing image
- [x] 5.2 Run `openspec validate exif-capture-time-and-geo --type change --strict` to verify spec compliance
