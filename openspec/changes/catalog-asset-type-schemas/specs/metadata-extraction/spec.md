## ADDED Requirements

### Requirement: Metadata extraction at registration
The system SHALL run a metadata extractor at registration time for every asset whose `(asset_type, format)` combination has a registered extractor. The extractor SHALL read lightweight metadata from the asset's URI (e.g., parquet footer, delta transaction log, lance manifest) and populate the `cached_metadata` column and `asset_columns` rows. Extraction failure SHALL be reported as a validation error and block registration.

#### Scenario: Successful parquet metadata extraction
- **WHEN** a table asset with `format: "parquet"` is registered and the URI points to a readable parquet file
- **THEN** the system SHALL extract `n_rows`, `n_columns`, `size_bytes`, and column schema (names, types, nullability) from the parquet metadata and store them in `cached_metadata` and `asset_columns`

#### Scenario: Successful delta metadata extraction
- **WHEN** a table asset with `format: "delta"` is registered and the URI points to a valid delta table
- **THEN** the system SHALL extract `n_rows`, `n_columns`, `column_schema`, `delta_version`, and `partition_columns` from the delta log and store them in `cached_metadata` and `asset_columns`

#### Scenario: Extraction failure blocks registration
- **WHEN** a table asset is registered but the metadata extractor cannot read the file (e.g., corrupted, incompatible version)
- **THEN** the system SHALL return 422 with a validation error indicating metadata extraction failed

### Requirement: Cached metadata data model
The system SHALL store system-derived metadata in a `cached_metadata` JSONB column on the `assets` table. The system SHALL also store a `metadata_cached_at` timestamp indicating when the metadata was last extracted. The structure of `cached_metadata` SHALL be determined by the `(asset_type, format)` combination. For table-type assets, `cached_metadata` SHALL include at minimum: `n_rows` (integer), `n_columns` (integer), `size_bytes` (integer or null), and format-specific fields.

#### Scenario: Cached metadata populated at registration
- **WHEN** a table asset is successfully registered
- **THEN** the `cached_metadata` column SHALL contain the extracted metadata and `metadata_cached_at` SHALL be set to the registration timestamp

#### Scenario: Format-specific cached metadata for delta
- **WHEN** a delta table asset is registered
- **THEN** `cached_metadata` SHALL additionally include `delta_version` (integer) and `partition_columns` (list of strings)

### Requirement: Metadata extraction replaces format sniff
The metadata extraction step SHALL replace the existing format sniff validation check. The `format_sniff` check in the validation report SHALL be replaced by a `metadata_extraction` check. If extraction succeeds, the check passes. If extraction fails, the check fails with the extraction error message.

#### Scenario: Extraction success replaces sniff pass
- **WHEN** metadata extraction succeeds for a parquet table
- **THEN** the validation report SHALL show `metadata_extraction: { passed: true }` instead of `format_sniff`

#### Scenario: Extraction failure replaces sniff failure
- **WHEN** metadata extraction fails for a delta table (e.g., no `_delta_log/` found)
- **THEN** the validation report SHALL show `metadata_extraction: { passed: false, message: "..." }` instead of `format_sniff`

### Requirement: On-demand metadata refresh
The system SHALL provide `POST /api/v1/assets/{id}/refresh-metadata` which re-runs the metadata extractor for the asset's `(asset_type, format)` against its stored URI, updates `cached_metadata` and `asset_columns` derived fields (name, type, nullable, ordinal), and updates `metadata_cached_at`. Declared annotations in `asset_columns` (description, semantic_type, unit, ref_*) SHALL be preserved. The caller SHALL have write permission on the asset's datastack.

#### Scenario: Refresh updates row count for appended delta table
- **WHEN** a delta table has had rows appended since registration, and an authorized user POSTs to `/api/v1/assets/{id}/refresh-metadata`
- **THEN** the system SHALL re-extract metadata, update `cached_metadata.n_rows` to the new count, update `metadata_cached_at`, and return the updated metadata

#### Scenario: Refresh preserves declared annotations
- **WHEN** a metadata refresh runs and a column `pre_pt_root_id` has a declared description and references annotation
- **THEN** the system SHALL update the derived fields (type, nullable) if they changed but SHALL preserve the declared `description`, `semantic_type`, `unit`, and `ref_*` fields

#### Scenario: Refresh detects new columns
- **WHEN** a metadata refresh runs and the file now contains a column `new_col` not previously in `asset_columns`
- **THEN** the system SHALL add a new row in `asset_columns` for `new_col` with derived fields populated and declared fields as NULL

#### Scenario: Refresh detects dropped columns
- **WHEN** a metadata refresh runs and a column `old_col` in `asset_columns` no longer exists in the file
- **THEN** the system SHALL preserve the `asset_columns` row for `old_col` but mark it as stale (e.g., set a `stale` boolean or add to a warnings response)

#### Scenario: Unauthorized refresh
- **WHEN** a user without write permission on the asset's datastack attempts a metadata refresh
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Cached metadata in asset responses
The system SHALL include `cached_metadata` and `metadata_cached_at` in asset responses from `GET /api/v1/assets/{id}` and `GET /api/v1/assets/`.

#### Scenario: Asset response includes cached metadata
- **WHEN** an authorized user GETs `/api/v1/assets/{id}` for an asset with cached metadata
- **THEN** the response SHALL include `cached_metadata` and `metadata_cached_at` fields
