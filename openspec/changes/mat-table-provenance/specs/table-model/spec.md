## MODIFIED Requirements

### Requirement: Table data model with single table inheritance
The system SHALL store tables using single table inheritance: table-specific columns are nullable columns on the shared `assets` table. `format` (TEXT) and `mat_version` (INTEGER) are base Asset fields shared across all asset types (nullable, since not all asset types require them). The `assets` table SHALL include the following table-specific nullable columns: `source` (TEXT, default `"user"` — enum: `"user"`, `"materialization"`), `source_table` (TEXT, nullable — the materialization table name this asset is a copy of), `cached_metadata` (JSONB), `metadata_cached_at` (TIMESTAMPTZ), and `column_annotations` (JSONB). The `asset_type` column SHALL serve as the polymorphic discriminator. SQLAlchemy SHALL use a `Table` subclass with `polymorphic_identity="table"` sharing the same `assets` table.

#### Scenario: Table asset created with source_table
- **WHEN** a table asset is registered with `source: "materialization"` and `source_table: "synapses"`
- **THEN** the system SHALL insert a row into `assets` with `asset_type = "table"`, `source = "materialization"`, and `source_table = "synapses"`

#### Scenario: User table has null source_table
- **WHEN** a table asset is registered with `source: "user"`
- **THEN** the system SHALL insert a row with `source_table = null`

#### Scenario: Non-table asset ignores table columns
- **WHEN** a non-table asset is registered
- **THEN** the system SHALL insert a row into `assets` with table-specific columns set to NULL

### Requirement: Column annotations structure
The `column_annotations` JSONB column SHALL store an array of annotation objects, each containing: `column_name` (string, required), `description` (string or null), `kind` (a `ColumnKind` object or null — semantic type only), and `links` (array of `ColumnLink` objects, default empty). Column annotations SHALL persist across metadata refreshes — refreshing `cached_metadata` SHALL NOT modify `column_annotations`.

#### Scenario: Annotations persist across refresh
- **WHEN** a table's cached metadata is refreshed
- **THEN** the `column_annotations` field SHALL remain unchanged

#### Scenario: Column annotation with kind and links
- **WHEN** a user adds an annotation for column `root_id` with `kind: {kind: "segmentation", node_level: "root_id"}` and `links: [{link_type: "copy_of", target_table: "synapses", target_column: "root_id"}]`
- **THEN** the system SHALL store both the kind and the link independently on the same annotation

#### Scenario: Column annotation with kind only
- **WHEN** a user adds an annotation with a kind but no links
- **THEN** the system SHALL store the kind and an empty links array

#### Scenario: Column annotation with links only
- **WHEN** a user adds an annotation for a computed column with links but `kind: null`
- **THEN** the system SHALL store null kind and the provided links

### Requirement: Read-time column merging
When returning a table asset via the API, the system SHALL merge `cached_metadata.columns` with `column_annotations` by matching on `column_name`. The merged result SHALL present each column with its `name`, `dtype` (from cached metadata), `description` (from annotations, or null), `kind` (from annotations, or null), and `links` (from annotations, or empty array). Columns present in cached metadata but absent from annotations SHALL have null description, null kind, and empty links. Annotations for column names not present in cached metadata SHALL be silently omitted from the merged output.

#### Scenario: Column with full annotation
- **WHEN** a table has a cached column `{name: "root_id", dtype: "int64"}` and an annotation `{column_name: "root_id", kind: {kind: "segmentation", node_level: "root_id"}, links: [...]}`
- **THEN** the API response SHALL include `{name: "root_id", dtype: "int64", kind: {...}, links: [...]}`

#### Scenario: Column without annotation
- **WHEN** a table has a cached column `{name: "x", dtype: "float64"}` with no matching annotation
- **THEN** the API response SHALL include `{name: "x", dtype: "float64", description: null, kind: null, links: []}`

#### Scenario: Orphaned annotation silently omitted
- **WHEN** an annotation exists for column `"old_col"` but `cached_metadata.columns` does not contain `"old_col"`
- **THEN** the API response SHALL NOT include an entry for `"old_col"`
