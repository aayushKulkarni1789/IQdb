## ADDED Requirements

### Requirement: EXIF metadata columns are populated during ingestion
The `Image` table SHALL include `capture_time` (TIMESTAMPTZ), `latitude` (DOUBLE PRECISION), and `longitude` (DOUBLE PRECISION) columns, populated during background processing by extracting EXIF metadata. All three fields SHALL be nullable and exposed in the `ImagePublic` API response schema.

Feature: image-search
Rule: EXIF extraction runs during the existing process_upload_embeddings step; failures produce NULL rather than aborting ingestion

#### Scenario: Capture time is extracted from DateTimeOriginal + OffsetTimeOriginal
- **GIVEN** an uploaded image with EXIF `DateTimeOriginal` (0x9003) and `OffsetTimeOriginal` (0x9011) tags
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to the parsed datetime with the correct timezone offset

#### Scenario: Fallback to DateTimeDigitized when DateTimeOriginal is absent
- **GIVEN** an uploaded image with EXIF `DateTimeDigitized` (0x9004) and `OffsetTimeDigitized` (0x9012) but no `DateTimeOriginal`
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set using `DateTimeDigitized` as the fallback source

#### Scenario: Capture time is NULL when datetime tag lacks offset
- **GIVEN** an uploaded image with EXIF `DateTimeOriginal` but no `OffsetTimeOriginal`
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to NULL

#### Scenario: Capture time is NULL when no datetime tags are present
- **GIVEN** an uploaded image with no EXIF datetime tags
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to NULL

#### Scenario: GPS coordinates are extracted and validated
- **GIVEN** an uploaded image with EXIF GPS IFD containing valid latitude and longitude
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `latitude` and `longitude` are set to signed decimal degrees

#### Scenario: GPS coordinates are NULL when out of bounds
- **GIVEN** an uploaded image with EXIF GPS coordinates where latitude is outside [-90, 90] or longitude outside [-180, 180]
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** both `latitude` and `longitude` are set to NULL

#### Scenario: GPS coordinates are NULL when IFD is absent
- **GIVEN** an uploaded image with no EXIF GPS IFD
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** both `latitude` and `longitude` are set to NULL

### Requirement: EXIF fields are exposed in the ImagePublic API schema
The `ImagePublic` API response schema SHALL include `capture_time`, `latitude`, and `longitude` fields alongside existing fields.

Feature: image-search
Rule: new fields are nullable and match the column types

#### Scenario: ImagePublic response includes capture_time and geo fields
- **GIVEN** an image record with non-NULL `capture_time`, `latitude`, and `longitude`
- **WHEN** the API returns the image via `ImagePublic`
- **THEN** the response includes `capture_time` as an ISO-8601 timestamp with timezone
- **AND** `latitude` and `longitude` are returned as floats

## MODIFIED Requirements

### Requirement: Datetime, geo, and face filters are registered stubs
`DatetimeFilter`, `GeoFilter`, and `FaceFilter` MUST be registered in the filter registry so their contract and tool surface exist, but their `build_predicate` SHALL be unimplemented and rejected at add-time. EXIF metadata (`capture_time`, `latitude`, `longitude`) is now populated during ingestion, but filter query logic remains deferred.

Feature: image-search
Rule: stubs are advertised as not live and fail fast at add-time; underlying data columns are now populated

#### Scenario: A stub filter is rejected at add-time
- **GIVEN** a registered stub filter (datetime, geo, or face)
- **WHEN** the agent calls `POST /sessions/{id}/filters` with that filter kind
- **THEN** the API returns `501 Not Implemented`
- **AND** the spec is not appended to the session

#### Scenario: The registry advertises which filters are live
- **GIVEN** the filter registry
- **WHEN** the agent inspects available filters
- **THEN** `ClipRank` is advertised as live
- **AND** `DatetimeFilter`, `GeoFilter`, and `FaceFilter` are advertised as not implemented

## REMOVED Requirements

<!-- None -->
