## MODIFIED Requirements

### Requirement: Register an asset
The `CatalogClient` SHALL provide a `register_asset()` method accepting `name`, `uri`, `format`, `asset_type`, `is_managed`, and optional `mat_version`, `revision` (default 1), `mutability` (default "static"), `maturity` (default "stable"), `properties`, `column_annotations`, and `expires_at`. The `properties` field SHALL require a `description` key for table-type assets. The `column_annotations` field SHALL be an optional dictionary keyed by column name, where each value contains optional `description`, `semantic_type`, `unit`, and `references` fields. It SHALL POST to the registration endpoint and return the created asset record including column metadata. The datastack is inherited from the client configuration.

#### Scenario: Register a Delta table with column annotations
- **WHEN** a user calls `client.catalog.register_asset(name="synapses", mat_version=943, uri="gs://bucket/path/", format="delta", asset_type="table", is_managed=True, properties={"description": "Synapse locations"}, column_annotations={"pre_pt_root_id": {"description": "Root ID of pre neuron", "references": {"table": "nucleus_detection_v0", "column": "pt_root_id"}}})`
- **THEN** the method SHALL POST to the catalog API and return the created asset record with column metadata

#### Scenario: Register a table without column annotations
- **WHEN** a user calls `client.catalog.register_asset(name="synapses", mat_version=943, uri="gs://bucket/path/", format="delta", asset_type="table", is_managed=True, properties={"description": "Synapse locations"})`
- **THEN** the method SHALL POST to the catalog API and return the created asset record with derived column metadata (no declared annotations)

### Requirement: Validate an asset before registration
The `CatalogClient` SHALL provide a `validate_asset()` method accepting the same parameters as `register_asset()`, including `column_annotations`. It SHALL POST to the server's `/api/v1/assets/validate` endpoint and return the structured validation report including type validation and metadata extraction checks, without creating an asset.

#### Scenario: Validate a table with type-specific checks
- **WHEN** a user calls `client.catalog.validate_asset(name="synapses", mat_version=943, uri="gs://bucket/path/", format="delta", asset_type="table", is_managed=True, properties={"description": "Synapse data"})`
- **THEN** the method SHALL return a validation report including `type_validation` and `metadata_extraction` check results

## ADDED Requirements

### Requirement: Get asset column metadata
The `CatalogClient` SHALL provide a method to retrieve column metadata for a table asset. The `get_asset()` method return value SHALL include a `columns` field containing the list of column records with both derived and declared metadata.

#### Scenario: Get asset with columns
- **WHEN** a user calls `client.catalog.get_asset("uuid-here")` for a table asset
- **THEN** the returned dictionary SHALL include a `columns` key with a list of column metadata objects

### Requirement: Refresh asset metadata
The `CatalogClient` SHALL provide a `refresh_metadata(asset_id)` method that POSTs to `/api/v1/assets/{id}/refresh-metadata` and returns the updated asset record with refreshed `cached_metadata` and column information.

#### Scenario: Refresh metadata for a mutable delta table
- **WHEN** a user calls `client.catalog.refresh_metadata("uuid-here")`
- **THEN** the method SHALL POST to the refresh endpoint and return the updated asset record with fresh `cached_metadata` and `metadata_cached_at`
