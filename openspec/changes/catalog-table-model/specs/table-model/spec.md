## ADDED Requirements

### Requirement: Table data model with joined inheritance
The system SHALL store tables using joined table inheritance: a `tables` DB table with a 1:1 foreign key (`asset_id`) to the `assets` table. The `tables` table SHALL contain: `format` (TEXT, required — e.g., `"delta"`, `"parquet"`), `mat_version` (INTEGER, nullable), `source` (TEXT, required, default `"user"` — enum: `"user"`, `"materialization"`), `cached_metadata` (JSONB, nullable), `metadata_cached_at` (TIMESTAMPTZ, nullable), and `column_annotations` (JSONB, nullable). The `assets` table SHALL use `asset_type` as a polymorphic discriminator column.

#### Scenario: Table created via joined inheritance
- **WHEN** a table asset is registered
- **THEN** the system SHALL insert a row into `assets` with `asset_type = "table"` and a corresponding row into `tables` with `format`, `mat_version`, and `source`

#### Scenario: Non-table asset has no tables row
- **WHEN** a non-table asset is registered
- **THEN** the system SHALL insert only a row into `assets` with no corresponding `tables` row

#### Scenario: Table query via join
- **WHEN** a table asset is queried by ID
- **THEN** the system SHALL join `assets` and `tables` to return all base and table-specific fields

### Requirement: Format-discriminated cached metadata
The `cached_metadata` JSONB column SHALL hold format-specific metadata whose shape varies by the `format` field. All formats SHALL include: `num_rows` (integer or null), `num_columns` (integer or null), `size_bytes` (integer or null), and `columns` (array of `{name: string, dtype: string}`). Delta tables SHALL additionally include: `delta_version` (integer), `partition_columns` (array of strings), `z_order_columns` (array of strings or null). Parquet tables SHALL additionally include: `row_group_count` (integer), `compression` (string). The system SHALL validate the cached metadata shape against the format at write time using application-layer Pydantic models.

#### Scenario: Delta table cached metadata shape
- **WHEN** a Delta table's metadata is extracted and cached
- **THEN** `cached_metadata` SHALL contain `num_rows`, `columns`, `delta_version`, and `partition_columns`

#### Scenario: Parquet table cached metadata shape
- **WHEN** a Parquet table's metadata is extracted and cached
- **THEN** `cached_metadata` SHALL contain `num_rows`, `columns`, `row_group_count`, and `compression`

### Requirement: Column annotations with column links
The `column_annotations` JSONB column SHALL store an array of annotation objects, each containing: `column_name` (string, required), `description` (string or null), and `links` (array of column link objects). Each column link object SHALL contain: `link_type` (string — e.g., `"foreign_key"`, `"derived_from"`), `target_table` (string — materialization table name), `target_column` (string), `target_datastack` (string or null — defaults to same datastack), and `target_mat_version` (integer or null). Column annotations SHALL persist across metadata refreshes — refreshing `cached_metadata` SHALL NOT modify `column_annotations`.

#### Scenario: Annotations persist across refresh
- **WHEN** a table's cached metadata is refreshed
- **THEN** the `column_annotations` field SHALL remain unchanged

#### Scenario: Column link structure
- **WHEN** a user adds a column link indicating `id` is a foreign key into `synapses.id`
- **THEN** the annotation entry for `id` SHALL contain a link with `link_type: "foreign_key"`, `target_table: "synapses"`, `target_column: "id"`

### Requirement: Read-time column merging
When returning a table asset via the API, the system SHALL merge `cached_metadata.columns` with `column_annotations` by matching on `column_name`. The merged result SHALL present each column with its `name`, `dtype` (from cached metadata), `description` (from annotations, or null), and `links` (from annotations, or empty array). Columns present in cached metadata but absent from annotations SHALL have null description and empty links. Annotations for column names not present in cached metadata SHALL be silently omitted from the merged output.

#### Scenario: Column with annotation
- **WHEN** a table has a cached column `{name: "id", dtype: "int64"}` and an annotation `{column_name: "id", description: "synapse ID", links: [...]}`
- **THEN** the API response SHALL include `{name: "id", dtype: "int64", description: "synapse ID", links: [...]}`

#### Scenario: Column without annotation
- **WHEN** a table has a cached column `{name: "x", dtype: "float64"}` with no matching annotation
- **THEN** the API response SHALL include `{name: "x", dtype: "float64", description: null, links: []}`

#### Scenario: Orphaned annotation silently omitted
- **WHEN** an annotation exists for column `"old_col"` but `cached_metadata.columns` does not contain `"old_col"`
- **THEN** the API response SHALL NOT include an entry for `"old_col"`
