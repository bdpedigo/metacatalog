## MODIFIED Requirements

### Requirement: Asset data model
The system SHALL store assets with the following required fields: `id` (UUID), `datastack` (string), `name` (string), `mat_version` (nullable integer — the CAVE materialization version, if applicable), `revision` (integer, default 1 — the asset's own iteration), `uri` (string), `format` (string, constrained to per-type enum), `asset_type` (string, constrained to enum), `owner` (string), `is_managed` (boolean), `mutability` (enum: `"static"` or `"mutable"`), `maturity` (enum: `"stable"`, `"draft"`, or `"deprecated"`), `properties` (JSON object, validated per asset_type/format), `cached_metadata` (nullable JSONB, system-derived), `metadata_cached_at` (nullable timestamp), and `created_at` (timestamp). The system SHALL also store optional fields: `expires_at` (timestamp) for TTL lifecycle and `access_group` (nullable string) for future per-asset permissions. Uniqueness SHALL be enforced via two partial unique indexes: `(datastack, name, mat_version, revision)` where `mat_version IS NOT NULL`, and `(datastack, name, revision)` where `mat_version IS NULL`.

#### Scenario: Unique constraint enforcement
- **WHEN** a registration request provides a `(datastack, name, mat_version, revision)` tuple that already exists
- **THEN** the system SHALL reject the request with a 409 Conflict response including the existing asset's ID

#### Scenario: Unique constraint with NULL mat_version
- **WHEN** two registration requests provide the same `(datastack, name, revision)` with `mat_version: null`
- **THEN** the system SHALL reject the second request with a 409 Conflict response

#### Scenario: Same name at different mat versions
- **WHEN** assets are registered with the same `(datastack, name, revision)` but different `mat_version` values
- **THEN** the system SHALL accept both registrations as distinct assets

#### Scenario: Optional expiry
- **WHEN** an asset is registered without an `expires_at` value
- **THEN** the system SHALL store the asset with a NULL `expires_at`, meaning it is retained indefinitely

#### Scenario: Cached metadata stored at registration
- **WHEN** an asset is successfully registered and metadata extraction succeeds
- **THEN** the system SHALL populate `cached_metadata` with extracted metadata and `metadata_cached_at` with the current timestamp

### Requirement: Asset registration with synchronous validation
The system SHALL accept asset registration via `POST /api/v1/assets/register` with a JSON body containing the required asset fields plus an optional `column_annotations` field for table-type assets. Registration SHALL perform synchronous validation in the following order: (1) caller authorization, (2) asset_type/format validation, (3) type-specific properties validation, (4) duplicate check, (5) URI reachability via HEAD request, (6) metadata extraction (replaces format sniff, also extracts column schema and stats), (7) source-conditional materialization checks. When `properties.source` is `"materialization"`, the system SHALL additionally verify the claimed mat table and version exist by querying the MaterializationEngine API. Validation SHALL complete within a reasonable synchronous timeout.

#### Scenario: Successful registration of a Delta table with column annotations
- **WHEN** an authorized user POSTs a valid registration with `format: "delta"`, `asset_type: "table"`, a reachable URI containing a valid delta log, `properties: { "description": "Synapse data" }`, and `column_annotations` for select columns
- **THEN** the system SHALL create the asset, populate `cached_metadata` and `asset_columns`, merge column annotations, and return 201 Created with the asset record

#### Scenario: Unreachable URI
- **WHEN** a registration request provides a URI that returns a non-success response to a HEAD request
- **THEN** the system SHALL return 422 with a validation error detail indicating `uri_reachable` check failed

#### Scenario: Metadata extraction failure
- **WHEN** a registration request claims `format: "delta"` but the URI does not contain a valid delta log
- **THEN** the system SHALL return 422 with a validation error detail indicating `metadata_extraction` check failed

#### Scenario: Materialization source verification
- **WHEN** a registration request has `properties.source: "materialization"` and `properties.source_table: "synapses_v2"` and `properties.mat_version: 943`
- **AND** the MaterializationEngine confirms that `synapses_v2` exists at version 943
- **THEN** the system SHALL create the asset and return 201 Created

#### Scenario: Materialization source verification failure
- **WHEN** a registration request has `properties.source: "materialization"` but the claimed mat table or version does not exist in MaterializationEngine
- **THEN** the system SHALL return 422 with a validation error detail indicating `mat_table_verify` check failed

#### Scenario: Unauthorized registration
- **WHEN** a caller without write permission on the specified datastack attempts to register an asset
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Asset retrieval by ID
The system SHALL provide `GET /api/v1/assets/{id}` to retrieve a single asset by its UUID. The system SHALL return 404 if the asset does not exist or has expired. For table-type assets, the response SHALL include `columns` (list of column metadata) and `cached_metadata`.

#### Scenario: Retrieve existing table asset
- **WHEN** an authorized user GETs `/api/v1/assets/{id}` for a valid, non-expired table asset
- **THEN** the system SHALL return the full asset record including `cached_metadata`, `metadata_cached_at`, and `columns`

#### Scenario: Retrieve expired asset
- **WHEN** an authorized user GETs `/api/v1/assets/{id}` for an asset whose `expires_at` is in the past
- **THEN** the system SHALL return 404
