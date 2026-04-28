## ADDED Requirements

### Requirement: Table data model with single table inheritance
The system SHALL store tables using single table inheritance: table-specific columns are nullable columns on the shared `assets` table. `format` (TEXT) and `mat_version` (INTEGER) are base Asset fields shared across all asset types (nullable, since not all asset types require them). The `assets` table SHALL include the following table-specific nullable columns: `source` (TEXT, default `"user"` — enum: `"user"`, `"materialization"`), `cached_metadata` (JSONB), `metadata_cached_at` (TIMESTAMPTZ), and `column_annotations` (JSONB). The `asset_type` column SHALL serve as the polymorphic discriminator. SQLAlchemy SHALL use a `Table` subclass with `polymorphic_identity="table"` sharing the same `assets` table.

#### Scenario: Table asset created
- **WHEN** a table asset is registered
- **THEN** the system SHALL insert a row into `assets` with `asset_type = "table"` and populate `format`, `mat_version`, `source`, and other table-specific columns

#### Scenario: Non-table asset ignores table columns
- **WHEN** a non-table asset is registered
- **THEN** the system SHALL insert a row into `assets` with table-specific columns set to NULL

#### Scenario: Table query returns table-specific fields
- **WHEN** a table asset is queried by ID
- **THEN** the system SHALL return all base and table-specific fields from the single `assets` row

### Requirement: Cached metadata structure
The `cached_metadata` JSONB column SHALL hold table metadata with a single unified shape across all formats. The structure SHALL include: `n_rows` (integer or null), `n_columns` (integer or null), `n_bytes` (integer or null), `columns` (array of `{name: string, dtype: string}`), and `partition_columns` (array of strings, default empty). There are no format-specific submodels — the same schema applies to Delta, Parquet, Lance, and any future format. If a format needs additional fields later, the model can be subclassed at that time. The system SHALL validate the cached metadata shape at write time using an application-layer Pydantic model.

#### Scenario: Table cached metadata shape
- **WHEN** a table's metadata is extracted and cached (any format)
- **THEN** `cached_metadata` SHALL contain `n_rows`, `n_columns`, `n_bytes`, `columns`, and `partition_columns`

### Requirement: Column annotations with column links
The `column_annotations` JSONB column SHALL store an array of annotation objects, each containing: `column_name` (string, required), `description` (string or null), and `links` (array of column link objects). Each column link object SHALL contain: `link_type` (string — e.g., `"foreign_key"`, `"derived_from"`), `target_table` (string — materialization table name), and `target_column` (string). Column links always reference tables within the same datastack as the asset. Column annotations SHALL persist across metadata refreshes — refreshing `cached_metadata` SHALL NOT modify `column_annotations`.

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
