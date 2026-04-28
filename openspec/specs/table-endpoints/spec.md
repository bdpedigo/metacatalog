## ADDED Requirements

### Requirement: Table preview endpoint
The system SHALL provide `POST /api/v1/tables/preview` accepting `uri` (string, required), `format` (string, required), and `datastack` (string, required). The endpoint SHALL extract metadata from the URI, validate the caller has read permission on the datastack, and return the discovered metadata (columns, row count, format-specific fields). The endpoint SHALL NOT create any records.

#### Scenario: Successful preview
- **WHEN** an authorized user POSTs a valid Delta Lake URI to the preview endpoint
- **THEN** the system SHALL return the discovered columns, row count, and Delta-specific metadata without creating a record

#### Scenario: Unauthorized preview
- **WHEN** a user without read permission on the datastack attempts a preview
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Table registration endpoint
The system SHALL provide `POST /api/v1/tables/register` accepting: `datastack`, `name`, `revision`, `uri`, `format`, `mat_version` (optional), `source` (optional, default `"user"`), `is_managed`, `mutability`, `maturity`, `access_group` (optional), `expires_at` (optional), and `column_annotations` (optional). The endpoint SHALL perform authorization, duplicate checking, metadata extraction, column link validation (if annotations provided), and then create an `assets` row with `asset_type="table"` and table-specific fields populated. It SHALL return 201 with the full table record including discovered metadata and merged column view.

#### Scenario: Successful table registration
- **WHEN** an authorized user registers a table with valid URI and format
- **THEN** the system SHALL create the asset row with table fields, extract metadata, and return 201 with the full record

#### Scenario: Duplicate table
- **WHEN** a table with the same `(datastack, name, mat_version, revision)` already exists
- **THEN** the system SHALL return 409 Conflict

### Requirement: Table annotation update endpoint
The system SHALL provide `PATCH /api/v1/tables/{id}/annotations` as specified in the `table-column-annotations` capability.

#### Scenario: Update annotations on existing table
- **WHEN** an authorized user PATCHes annotations for an existing table
- **THEN** the system SHALL replace `column_annotations` and return the updated table

### Requirement: Table metadata refresh endpoint
The system SHALL provide `POST /api/v1/tables/{id}/refresh` as specified in the `metadata-extraction` capability.

#### Scenario: Refresh metadata on existing table
- **WHEN** an authorized user triggers a refresh for a table
- **THEN** the system SHALL re-extract metadata and return the updated table

### Requirement: List tables endpoint
The system SHALL provide `GET /api/v1/tables/` for listing table assets. The endpoint SHALL accept query parameters: `datastack` (required), `name` (optional), `mat_version` (optional), `revision` (optional), `format` (optional), `source` (optional), `mutability` (optional), `maturity` (optional). The response SHALL include table-specific fields (`format`, `mat_version`, `source`, merged columns) for every result. Expired tables SHALL be excluded.

#### Scenario: List tables with format filter
- **WHEN** an authorized user GETs `/api/v1/tables/?datastack=minnie65_public&format=delta`
- **THEN** the system SHALL return all non-expired Delta tables for that datastack with full table-specific fields

#### Scenario: List tables filters by source
- **WHEN** an authorized user GETs `/api/v1/tables/?datastack=minnie65_public&source=materialization`
- **THEN** the system SHALL return only materialization-sourced tables
