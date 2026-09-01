## ADDED Requirements

### Requirement: Datetime filter spec validates field types and rejects inverted ranges
`DatetimeFilterSpec` SHALL accept optional independent fields `date_lower`, `date_upper` (`datetime.date`), `time_lower`, `time_upper` (`datetime.time`), and `days_included` (array of `DayOfWeek` enum values). All fields are independent — no pair constraints. The spec SHALL reject inverted ranges (`date_lower > date_upper`, `time_lower > time_upper`) with HTTP 422.

Feature: image-search
Rule: datetime filter fields are independently optional and ranges are validated

#### Scenario: A valid datetime spec with all fields is accepted
- **GIVEN** an open search session
- **WHEN** the agent applies a DATETIME filter with `date_lower`, `date_upper`, `time_lower`, `time_upper`, and `days_included`
- **THEN** the filter is accepted and appended to the session

#### Scenario: A datetime spec with only date range is accepted
- **GIVEN** an open search session
- **WHEN** the agent applies a DATETIME filter with only `date_lower` and `date_upper`
- **THEN** the filter is accepted and appended to the session

#### Scenario: A datetime spec with only time range is accepted
- **GIVEN** an open search session
- **WHEN** the agent applies a DATETIME filter with only `time_lower` and `time_upper`
- **THEN** the filter is accepted and appended to the session

#### Scenario: A datetime spec with only days_included is accepted
- **GIVEN** an open search session
- **WHEN** the agent applies a DATETIME filter with only `days_included` set to `["MONDAY", "WEDNESDAY"]`
- **THEN** the filter is accepted and appended to the session

#### Scenario: An inverted date range is rejected
- **GIVEN** an open search session
- **WHEN** the agent applies a DATETIME filter with `date_lower` after `date_upper`
- **THEN** the API returns `422` with a validation error indicating the inverted range
- **AND** no spec is appended to the session

#### Scenario: An inverted time range is rejected
- **GIVEN** an open search session
- **WHEN** the agent applies a DATETIME filter with `time_lower` after `time_upper`
- **THEN** the API returns `422` with a validation error indicating the inverted range
- **AND** no spec is appended to the session

### Requirement: Datetime filter generates SQL predicates over capture_time
`DatetimeFilter.build_predicate()` SHALL produce a conjunction of optional SQL WHERE clauses over `capture_time`: `DATE(capture_time) >= :date_lower`, `DATE(capture_time) <= :date_upper`, `TIME(capture_time) >= :time_lower`, `TIME(capture_time) <= :time_upper`, `EXTRACT(DOW FROM capture_time) IN (...)`. DOW mapping: `MONDAY=1, TUESDAY=2, ..., SUNDAY=0`. NULL `capture_time` rows are excluded by standard SQL NULL comparison semantics.

Feature: image-search
Rule: datetime predicates are AND-composed from provided fields only

#### Scenario: Date-only filter matches images within the date range
- **GIVEN** an image with `capture_time` of `2024-06-15 10:30:00`
- **WHEN** a datetime filter with `date_lower = 2024-06-01` and `date_upper = 2024-06-30` is applied
- **THEN** the image is included in the candidate set

#### Scenario: Time-only filter matches images within the time range
- **GIVEN** an image with `capture_time` of `2024-06-15 14:30:00`
- **WHEN** a datetime filter with `time_lower = 08:00:00` and `time_upper = 18:00:00` is applied
- **THEN** the image is included in the candidate set

#### Scenario: Day-of-week filter matches images taken on those days
- **GIVEN** an image with `capture_time` of `2024-06-17 10:00:00` (a Monday)
- **WHEN** a datetime filter with `days_included = ["MONDAY"]` is applied
- **THEN** the image is included in the candidate set

#### Scenario: Mixed filters compose with AND
- **GIVEN** an image with `capture_time` of `2024-06-15 14:30:00` (a Saturday)
- **WHEN** a datetime filter with `date_lower = 2024-06-01`, `time_lower = 08:00:00`, and `days_included = ["MONDAY"]` is applied
- **THEN** the image is excluded because Saturday is not in `days_included`

#### Scenario: Images with NULL capture_time are excluded
- **GIVEN** an image with `capture_time` set to NULL
- **WHEN** any datetime filter is applied
- **THEN** the image is excluded from the candidate set

## MODIFIED Requirements

### Requirement: Datetime, geo, and face filters are registered stubs
`DatetimeFilter` SHALL be a live subset filter that generates SQL WHERE clauses over `capture_time` with pydantic-validated specs and day-of-week filtering. `GeoFilter` and `FaceFilter` MUST remain registered stubs whose `build_predicate` SHALL be unimplemented and rejected at add-time. EXIF metadata (`capture_time`, `latitude`, `longitude`) is now populated during ingestion.

Feature: image-search
Rule: datetime filter is live; geo and face remain stubs; underlying data columns are populated

#### Scenario: The datetime filter is accepted at add-time
- **GIVEN** a registered live filter (datetime)
- **WHEN** the agent calls `POST /sessions/{id}/filters` with a DATETIME filter kind
- **THEN** the filter spec is validated and appended to the session
- **AND** the response returns the running `candidate_count`

#### Scenario: A stub filter is rejected at add-time
- **GIVEN** a registered stub filter (geo or face)
- **WHEN** the agent calls `POST /sessions/{id}/filters` with that filter kind
- **THEN** the API returns `501 Not Implemented`
- **AND** the spec is not appended to the session

#### Scenario: The registry advertises which filters are live
- **GIVEN** the filter registry
- **WHEN** the agent inspects available filters
- **THEN** `ClipRank` and `DatetimeFilter` are advertised as live
- **AND** `GeoFilter` and `FaceFilter` are advertised as not implemented

### Requirement: EXIF metadata columns are populated during ingestion
The `Image` table SHALL include `capture_time` (TIMESTAMP — naive local datetime), `latitude` (DOUBLE PRECISION), and `longitude` (DOUBLE PRECISION) columns, populated during background processing by extracting EXIF metadata. All three fields SHALL be nullable and exposed in the `ImagePublic` API response schema. Datetime and offset tags SHALL be read from the ExifIFD sub-IFD (`0x8769`) as well as the top-level IFD, with sub-IFD values taking precedence, so `capture_time` is populated for real camera and phone files that store tags in the sub-IFD.

Feature: image-search
Rule: EXIF extraction runs during the existing process_upload_embeddings step; failures produce NULL rather than aborting ingestion

#### Scenario: Capture time is extracted from DateTimeOriginal as naive local time
- **GIVEN** an uploaded image with EXIF `DateTimeOriginal` (0x9003) tag
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to the parsed local datetime without timezone info

#### Scenario: Capture time is extracted from tags in the ExifIFD sub-IFD
- **GIVEN** an uploaded image whose `DateTimeOriginal`, `OffsetTimeOriginal`, `DateTimeDigitized`, and `OffsetTimeDigitized` tags are stored in the ExifIFD sub-IFD (`0x8769`) and not at the top level
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set from the sub-IFD `DateTimeOriginal` tag as naive local time

#### Scenario: Fallback to DateTimeDigitized when DateTimeOriginal is absent or incomplete
- **GIVEN** an uploaded image whose `DateTimeOriginal` tag is absent or incomplete, and that has `DateTimeDigitized` (0x9004)
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set using `DateTimeDigitized` as the fallback source

#### Scenario: Capture time is NULL when no datetime tag is present
- **GIVEN** an uploaded image with no EXIF datetime tags
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to NULL

#### Scenario: Embeddings are stored for the correct image when a batch contains an unreadable file
- **GIVEN** an uploaded batch containing a file the ingestion pipeline cannot open and other valid images
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** each valid image receives the embedding computed from itself
- **AND** no embedding is stored for the unreadable file

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

#### Scenario: ImagePublic response includes capture_time as naive datetime
- **GIVEN** an image record with non-NULL `capture_time`, `latitude`, and `longitude`
- **WHEN** the API returns the image via `ImagePublic`
- **THEN** the response includes `capture_time` as an ISO-8601 timestamp without timezone
- **AND** `latitude` and `longitude` are returned as floats
