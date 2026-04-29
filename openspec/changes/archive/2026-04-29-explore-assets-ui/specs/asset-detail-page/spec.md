## ADDED Requirements

### Requirement: Asset detail page
The UI SHALL render a detail page at `/ui/explore/{id}` showing all fields for a single asset. The page SHALL include a "Back to list" link returning to `/ui/explore`. The page SHALL include an "Edit" button linking to `/ui/explore/{id}/edit`.

#### Scenario: User views table asset detail
- **WHEN** a user navigates to `/ui/explore/{id}` for a table asset
- **THEN** the system SHALL display the asset's summary fields, cached metadata section, and columns table

#### Scenario: User views non-table asset detail
- **WHEN** a user navigates to `/ui/explore/{id}` for a non-table asset (e.g., generic or view)
- **THEN** the system SHALL display the asset's summary fields and properties, without table-specific sections (cached metadata, columns)

#### Scenario: Asset not found
- **WHEN** a user navigates to `/ui/explore/{id}` with an invalid or expired asset ID
- **THEN** the system SHALL display a 404 error page

### Requirement: Summary section
The detail page SHALL display a summary card containing: asset_type, format, source (for tables), mat_version, revision, maturity, mutability, owner, created_at, expires_at, uri, is_managed, and access_group. Fields with NULL values SHALL be displayed as "—".

#### Scenario: Summary displays all identity fields
- **WHEN** a user views the detail page for a table asset with mat_version=1078, format="delta", source="materialization"
- **THEN** the summary card SHALL display all those fields with their values

### Requirement: Cached metadata section for tables
The detail page SHALL display a cached metadata section for table assets showing: n_rows (formatted with commas), n_columns, n_bytes (human-readable, e.g., "42.3 GB"), partition_columns (comma-separated list), and metadata_cached_at timestamp. This section SHALL only appear for `asset_type="table"` assets that have non-null `cached_metadata`.

#### Scenario: Metadata section with all fields populated
- **WHEN** a user views a table asset with cached_metadata `{n_rows: 337412891, n_columns: 14, n_bytes: 45400000000, partition_columns: ["pt_root_id"]}`
- **THEN** the system SHALL display "Rows: 337,412,891", "Columns: 14", "Size: 42.3 GB", "Partition columns: pt_root_id"

#### Scenario: No cached metadata
- **WHEN** a user views a table asset with null cached_metadata
- **THEN** the cached metadata section SHALL display "Metadata not yet extracted" with a note about using the refresh endpoint

### Requirement: Columns table for tables
The detail page SHALL display a table of merged columns for table assets. Each row SHALL show: column name, dtype, description (from annotations), and links (rendered as readable references, e.g., "→ nucleus_detection_v0.pt_root_id"). Columns without annotations SHALL show "—" for description and links.

#### Scenario: Columns table with annotations
- **WHEN** a user views a table asset with 14 columns, 3 of which have annotations
- **THEN** the columns table SHALL list all 14 columns with dtype, and the 3 annotated columns SHALL show their descriptions and links

#### Scenario: Column link display
- **WHEN** a column has a link with `{link_type: "foreign_key", target_table: "nucleus_detection_v0", target_column: "pt_root_id"}`
- **THEN** the link SHALL be displayed as "→ nucleus_detection_v0.pt_root_id"
