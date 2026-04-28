## MODIFIED Requirements

### Requirement: Register an asset
The `CatalogClient` SHALL provide a `register_asset()` method accepting `name`, `uri`, `asset_type`, `is_managed`, and optional `revision` (default 1), `mutability` (default `"static"`), `maturity` (default `"stable"`), `format`, `mat_version`, `properties`, and `expires_at`. The `format` and `mat_version` parameters remain as optional base Asset fields (not table-specific). The datastack is inherited from the client configuration.

#### Scenario: Register a non-table asset
- **WHEN** a user calls `client.catalog.register_asset(name="my_mesh", uri="gs://bucket/mesh/", asset_type="mesh", is_managed=False)`
- **THEN** the method SHALL POST to the asset registration endpoint and return the created asset record

## ADDED Requirements

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
