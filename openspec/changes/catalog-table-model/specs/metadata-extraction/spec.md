## ADDED Requirements

### Requirement: Metadata extraction from Delta Lake tables
The system SHALL extract metadata from Delta Lake tables by reading the Delta transaction log at the given URI. Extracted metadata SHALL include: `num_rows`, `num_columns`, `size_bytes`, `columns` (name and dtype for each column), `delta_version` (latest committed version), `partition_columns`, and `z_order_columns` (if available). The extractor SHALL use the caller's credentials (or service credentials for managed assets) to access cloud storage.

#### Scenario: Successful Delta metadata extraction
- **WHEN** the system extracts metadata from a valid Delta Lake URI
- **THEN** the result SHALL include the column schema, row count, delta version, and partition columns read from the Delta log

#### Scenario: Inaccessible Delta URI
- **WHEN** the system attempts to extract metadata from a Delta Lake URI it cannot access
- **THEN** the extraction SHALL fail with an error indicating the URI is not reachable or not readable

### Requirement: Metadata extraction from Parquet files
The system SHALL extract metadata from Parquet files by reading the Parquet footer at the given URI. Extracted metadata SHALL include: `num_rows`, `num_columns`, `size_bytes`, `columns` (name and dtype), `row_group_count`, and `compression`. For partitioned Parquet datasets (directories of Parquet files), the system SHALL read metadata from a representative file.

#### Scenario: Successful Parquet metadata extraction
- **WHEN** the system extracts metadata from a valid Parquet file URI
- **THEN** the result SHALL include the column schema, row count, row group count, and compression read from the Parquet footer

### Requirement: Metadata extraction at preview
The `POST /api/v1/tables/preview` endpoint SHALL trigger metadata extraction for the provided URI and format. The extracted metadata SHALL be returned in the response. The preview SHALL NOT create any asset record or store any data.

#### Scenario: Preview returns discovered metadata
- **WHEN** a user POSTs a URI and format to the preview endpoint
- **THEN** the system SHALL extract metadata and return the columns, row count, and format-specific fields without creating a record

### Requirement: Metadata extraction at registration
The `POST /api/v1/tables/register` endpoint SHALL trigger fresh metadata extraction during registration. The extracted metadata SHALL be stored in the `cached_metadata` field of the created table record. The system SHALL NOT reuse cached results from a prior preview request.

#### Scenario: Registration extracts and caches metadata
- **WHEN** a user registers a table
- **THEN** the system SHALL extract metadata from the URI at registration time and store it in `cached_metadata` with `metadata_cached_at` set to the current time

### Requirement: Manual metadata refresh
The system SHALL provide `POST /api/v1/tables/{id}/refresh` to re-extract metadata for an existing table asset. The system SHALL replace the `cached_metadata` JSONB and update `metadata_cached_at`. The system SHALL NOT modify `column_annotations`.

#### Scenario: Successful refresh
- **WHEN** an authorized user POSTs to the refresh endpoint for a table asset
- **THEN** the system SHALL re-extract metadata from the table's URI, replace `cached_metadata`, update `metadata_cached_at`, and leave `column_annotations` unchanged

#### Scenario: Refresh of non-table asset
- **WHEN** a user attempts to refresh a non-table asset
- **THEN** the system SHALL return 400 Bad Request
