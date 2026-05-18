## MODIFIED Requirements

### Requirement: Asset data model
The system SHALL store assets with the following required fields: `id` (UUID), `datastack` (string), `name` (string), `revision` (integer, default 1), `uri` (string), `asset_type` (string — polymorphic discriminator), `owner` (string), `is_managed` (boolean), `mutability` (enum: `"static"` or `"mutable"`), `maturity` (enum: `"stable"`, `"draft"`, or `"deprecated"`), `properties` (JSON object), and `created_at` (timestamp). The system SHALL also store optional base fields: `format` (TEXT, nullable — storage format, e.g. `"delta"`, `"parquet"`, `"precomputed"`; valid values vary by asset type), `mat_version` (INTEGER, nullable), `expires_at` (timestamp) for TTL lifecycle, and `access_group` (nullable string) for per-asset permissions. The `assets` table SHALL also include table-specific nullable columns: `source` (TEXT), `source_table` (TEXT, nullable — the materialization table name this asset is a copy of), `cached_metadata` (JSONB), `metadata_cached_at` (TIMESTAMPTZ), and `column_annotations` (JSONB) — these are populated only for table assets and NULL for other asset types. The `asset_type` column SHALL serve as the polymorphic discriminator for single table inheritance. Uniqueness SHALL be enforced via partial unique index on `(datastack, name, mat_version, revision)` where `mat_version IS NOT NULL`, and a partial unique index on `(datastack, name, revision)` where `mat_version IS NULL`.

#### Scenario: Unique constraint enforcement
- **WHEN** a registration request provides a `(datastack, name, mat_version, revision)` tuple that already exists
- **THEN** the system SHALL reject the request with a 409 Conflict response including the existing asset's ID

#### Scenario: Unique constraint with NULL mat_version
- **WHEN** two registration requests provide the same `(datastack, name, revision)` with `mat_version: null`
- **THEN** the system SHALL reject the second request with a 409 Conflict response

#### Scenario: Same name at different mat versions
- **WHEN** assets are registered with the same `(datastack, name, revision)` but different `mat_version` values
- **THEN** the system SHALL accept both registrations as distinct assets

#### Scenario: source_table stored on mat-sourced asset
- **WHEN** a table asset is registered with `source: "materialization"` and `source_table: "synapses"`
- **THEN** the system SHALL store `source_table = "synapses"` on the asset record

#### Scenario: source_table null on user asset
- **WHEN** a table asset is registered with `source: "user"`
- **THEN** the system SHALL store `source_table = null`

### Requirement: Asset registration with synchronous validation
The system SHALL accept asset registration via `POST /api/v1/assets/register` with a JSON body containing the required asset fields. Registration SHALL perform synchronous validation in the following order: (1) caller authorization, (2) duplicate check, (3) URI reachability via HEAD request, (4) format sniff by checking for format-specific metadata (e.g., `_delta_log/` for Delta, `info` file for precomputed). When `properties.source` is `"materialization"`, the system SHALL additionally verify the claimed mat table and version exist by querying the MaterializationEngine API, and SHALL require `source_table` to be present and non-null. Validation SHALL complete within a reasonable synchronous timeout.

#### Scenario: Successful registration of a Delta table
- **WHEN** an authorized user POSTs a valid registration with `format: "delta"` and a reachable URI containing a `_delta_log/` directory
- **THEN** the system SHALL create the asset and return 201 Created with the asset record including its generated `id`

#### Scenario: Materialization source requires source_table
- **WHEN** a registration request has `source: "materialization"` but omits `source_table`
- **THEN** the system SHALL return 422 with a validation error indicating `source_table` is required when `source` is `"materialization"`

#### Scenario: Materialization source verification
- **WHEN** a registration request has `source: "materialization"`, `source_table: "synapses_v2"`, and `mat_version: 943`
- **AND** the MaterializationEngine confirms that `synapses_v2` exists at version 943
- **THEN** the system SHALL create the asset and return 201 Created

#### Scenario: Materialization source verification failure
- **WHEN** a registration request has `source: "materialization"` but the claimed mat table or version does not exist in MaterializationEngine
- **THEN** the system SHALL return 422 with a validation error detail indicating `mat_table_verify` check failed

## ADDED Requirements

### Requirement: Asset listing filter by source_table
The asset listing endpoint (`GET /api/v1/assets/`) SHALL accept an optional `source_table` query parameter (exact match). When provided, the system SHALL return only assets where `source_table` matches the given value.

#### Scenario: Filter by source_table
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65&source_table=synapses`
- **THEN** the system SHALL return only assets with `source_table = "synapses"` in that datastack

#### Scenario: Filter by source_table and mat_version
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65&source_table=synapses&mat_version=943`
- **THEN** the system SHALL return all static copies of the `synapses` table at version 943, regardless of asset name or layout variant
