## MODIFIED Requirements

### Requirement: EXIF metadata columns are populated during ingestion
The `Image` table SHALL include `capture_time` (TIMESTAMPTZ), `latitude` (DOUBLE PRECISION), and `longitude` (DOUBLE PRECISION) columns, populated during background processing by extracting EXIF metadata. All three fields SHALL be nullable and exposed in the `ImagePublic` API response schema. Datetime and offset tags SHALL be read from the ExifIFD sub-IFD (`0x8769`) as well as the top-level IFD, with sub-IFD values taking precedence, so `capture_time` is populated for real camera and phone files that store tags in the sub-IFD.

Feature: image-search
Rule: EXIF extraction runs during the existing process_upload_embeddings step; failures produce NULL rather than aborting ingestion

#### Scenario: Capture time is extracted from DateTimeOriginal + OffsetTimeOriginal
- **GIVEN** an uploaded image with EXIF `DateTimeOriginal` (0x9003) and `OffsetTimeOriginal` (0x9011) tags
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to the parsed datetime with the correct timezone offset

#### Scenario: Capture time is extracted from tags in the ExifIFD sub-IFD
- **GIVEN** an uploaded image whose `DateTimeOriginal`, `OffsetTimeOriginal`, `DateTimeDigitized`, and `OffsetTimeDigitized` tags are stored in the ExifIFD sub-IFD (`0x8769`) and not at the top level
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set from the sub-IFD `DateTimeOriginal` and `OffsetTimeOriginal` tags with the correct timezone offset

#### Scenario: Fallback to DateTimeDigitized when DateTimeOriginal is absent or incomplete
- **GIVEN** an uploaded image whose `DateTimeOriginal` tag is absent or lacks a matching offset, and that has `DateTimeDigitized` (0x9004) with `OffsetTimeDigitized` (0x9012)
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set using `DateTimeDigitized` as the fallback source

#### Scenario: Capture time is NULL when no datetime pair is complete
- **GIVEN** an uploaded image with `DateTimeOriginal` but no `OffsetTimeOriginal` and with no complete `DateTimeDigitized`/`OffsetTimeDigitized` pair
- **WHEN** the background ingestion pipeline processes the upload
- **THEN** `capture_time` is set to NULL

#### Scenario: Capture time is NULL when no datetime tags are present
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
