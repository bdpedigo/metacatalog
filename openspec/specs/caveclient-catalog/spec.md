## ADDED Requirements

### Requirement: CAVEclient catalog sub-client
CAVEclient SHALL expose a `client.catalog` property that returns a `CatalogClient` instance configured with the active datastack and middle_auth token.

#### Scenario: Accessing the catalog client
- **WHEN** a user creates a `CAVEclient("minnie65_public")` and accesses `client.catalog`
- **THEN** the system SHALL return a `CatalogClient` bound to datastack `minnie65_public` with the user's auth token

### Requirement: List and filter assets
The `CatalogClient` SHALL provide a `list_assets()` method that returns a list of asset metadata dictionaries. It SHALL accept optional keyword arguments: `name`, `mat_version`, `revision`, `format`, `asset_type`, `mutability`, `maturity`. The datastack is inherited from the client configuration.

#### Scenario: List all assets
- **WHEN** a user calls `client.catalog.list_assets()`
- **THEN** the method SHALL return all non-expired assets for the configured datastack

#### Scenario: Filter by name and mat_version
- **WHEN** a user calls `client.catalog.list_assets(name="synapses", mat_version=943)`
- **THEN** the method SHALL return all revisions of synapses at mat version 943 for the configured datastack

### Requirement: Get asset by ID
The `CatalogClient` SHALL provide a `get_asset(asset_id)` method that returns the full asset record as a dictionary.

#### Scenario: Get existing asset
- **WHEN** a user calls `client.catalog.get_asset("uuid-here")`
- **THEN** the method SHALL return the asset record dictionary

### Requirement: Register an asset
The `CatalogClient` SHALL provide a `register_asset()` method accepting `name`, `uri`, `asset_type`, `is_managed`, and optional `revision` (default 1), `mutability` (default `"static"`), `maturity` (default `"stable"`), `format`, `mat_version`, `properties`, and `expires_at`. The `format` and `mat_version` parameters remain as optional base Asset fields (not table-specific). The datastack is inherited from the client configuration.

#### Scenario: Register a non-table asset
- **WHEN** a user calls `client.catalog.register_asset(name="my_mesh", uri="gs://bucket/mesh/", asset_type="mesh", is_managed=False)`
- **THEN** the method SHALL POST to the asset registration endpoint and return the created asset record

### Requirement: Validate an asset before registration
The `CatalogClient` SHALL provide a `validate_asset()` method accepting the same parameters as `register_asset()`. It SHALL POST to the server's `/api/v1/assets/validate` endpoint and return the structured validation report without creating an asset.

#### Scenario: Validate a table before registering
- **WHEN** a user calls `client.catalog.validate_asset(name="synapses", mat_version=943, uri="gs://bucket/path/", format="delta", asset_type="table", is_managed=True)`
- **THEN** the method SHALL return a validation report with pass/fail status for each check

### Requirement: Delete an asset
The `CatalogClient` SHALL provide a `delete_asset(asset_id)` method that DELETEs the asset from the catalog and returns None on success.

#### Scenario: Delete an asset
- **WHEN** a user calls `client.catalog.delete_asset("uuid-here")`
- **THEN** the method SHALL DELETE the catalog entry and return None

### Requirement: Future materialization-compatible query interface
The `CatalogClient` design SHALL NOT preclude a future convenience layer that provides a query interface compatible with the existing `client.materialize.query_table()` API, backed by catalog-hosted table dumps rather than the MaterializationEngine. This future layer would use an opinionated query engine (e.g., Polars) for execution but would not lock users into that choice — users who prefer DuckDB or other tools can use the standard credential vending and view resolution APIs directly. This requirement is a design constraint for future compatibility, not a Phase 0-2 deliverable.

#### Scenario: Future compatibility is preserved
- **WHEN** a materialization table dump is registered in the catalog with `properties.source: "materialization"` and the appropriate `mat_version`
- **THEN** sufficient metadata SHALL exist in the asset record for a future client-side wrapper to locate, authenticate, and query the table without additional catalog API changes

### Requirement: Register a table
The `CatalogClient` SHALL provide a `register_table()` method accepting `name`, `uri`, `format`, and optional `mat_version`, `source` (default `"user"`), `revision` (default 1), `is_managed` (default True), `mutability`, `maturity`, `access_group`, `expires_at`, and `column_annotations`. The datastack is inherited from the client configuration. It SHALL POST to `POST /api/v1/tables/register` and return the full table record including discovered metadata and merged columns.

#### Scenario: Register a Delta table
- **WHEN** a user calls `client.catalog.register_table(name="synapses", uri="gs://bucket/synapses/", format="delta", mat_version=943)`
- **THEN** the method SHALL POST to the table registration endpoint and return the record with discovered columns, row count, and Delta metadata

### Requirement: Preview a table
The `CatalogClient` SHALL provide a `preview_table()` method accepting `uri` and `format`. The datastack is inherited from the client configuration. It SHALL POST to `POST /api/v1/tables/preview` and return the discovered metadata without creating a record.

#### Scenario: Preview a table
- **WHEN** a user calls `client.catalog.preview_table(uri="gs://bucket/my_table/", format="delta")`
- **THEN** the method SHALL return the discovered columns, row count, and format-specific metadata

### Requirement: List tables
The `CatalogClient` SHALL provide a `list_tables()` method accepting optional `name`, `mat_version`, `revision`, `format`, `source`, `mutability`, `maturity`. The datastack is inherited from the client configuration. It SHALL GET `/api/v1/tables/` and return table records with full table-specific fields.

#### Scenario: List Delta tables
- **WHEN** a user calls `client.catalog.list_tables(format="delta")`
- **THEN** the method SHALL return all non-expired Delta tables for the configured datastack

### Requirement: Update column annotations
The `CatalogClient` SHALL provide an `update_annotations(asset_id, column_annotations)` method that PATCHes `/api/v1/tables/{id}/annotations` with replace semantics. It SHALL return the updated table record.

#### Scenario: Add a column description
- **WHEN** a user calls `client.catalog.update_annotations(asset_id, [{"column_name": "id", "description": "synapse ID", "links": []}])`
- **THEN** the method SHALL replace the stored annotations and return the updated table

### Requirement: Refresh table metadata
The `CatalogClient` SHALL provide a `refresh_metadata(asset_id)` method that POSTs to `/api/v1/tables/{id}/refresh` and returns the updated table record with fresh cached metadata.

#### Scenario: Refresh metadata
- **WHEN** a user calls `client.catalog.refresh_metadata(asset_id)`
- **THEN** the method SHALL trigger re-extraction and return the table with updated metadata
