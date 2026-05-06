## ADDED Requirements

### Requirement: Discover specs endpoint
The system SHALL provide `POST /materialize/deltalake/discover-specs` accepting `{ datastack, version, table_name, target_partition_size_mb }`. The endpoint SHALL require `dataset_admin` permission for the specified datastack. The endpoint SHALL run `discover_default_output_specs()` against the frozen DB, estimate bytes per row, resolve partition counts using the provided `target_partition_size_mb`, and return the results without enqueuing any Celery task.

#### Scenario: Successful discovery
- **WHEN** an authorized admin POSTs valid datastack, version, and table_name
- **THEN** the system SHALL return `{ row_count, bytes_per_row, specs: [...] }` with each spec containing `partition_by`, `partition_strategy`, `n_partitions` (resolved), `zorder_columns`, `bloom_filter_columns`, `source_geometry_column`, and `source_table`

#### Scenario: Table not found
- **WHEN** the specified table does not exist in the frozen DB for that version
- **THEN** the system SHALL return 404 with an error message

#### Scenario: Version not found
- **WHEN** the specified version does not exist for the datastack
- **THEN** the system SHALL return 404 with an error message

#### Scenario: Unauthorized user
- **WHEN** a user without `dataset_admin` permission calls the endpoint
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Discovery result caching
The system SHALL cache the discovery result in Redis with key `deltalake_specs:{datastack}:v{version}:{table}` and a TTL of 10 minutes. Subsequent calls with the same parameters within the TTL SHALL return the cached result without re-querying the frozen DB.

#### Scenario: Cached result returned
- **WHEN** a discovery request matches a cached result within TTL
- **THEN** the system SHALL return the cached result without querying the frozen DB

#### Scenario: Cache expired
- **WHEN** a discovery request is made after the TTL has expired
- **THEN** the system SHALL re-run discovery against the frozen DB and cache the new result

### Requirement: Recalculate endpoint
The system SHALL provide `POST /materialize/deltalake/recalculate` accepting `{ row_count, bytes_per_row, specs }` where each spec includes optional `target_file_size_mb` and `n_partitions` (which may be `"auto"` or a number). The endpoint SHALL resolve `n_partitions` for each spec where it is `"auto"` using `resolve_n_partitions()` with the spec's `target_file_size_mb` (or a global default). The endpoint SHALL NOT access any database.

#### Scenario: Recalculate with auto partitions
- **WHEN** a spec has `n_partitions: "auto"` and `target_file_size_mb: 128`
- **THEN** the system SHALL compute `n_partitions = ceil(row_count * bytes_per_row / (128 * 1024 * 1024))` and return the resolved value

#### Scenario: Explicit n_partitions preserved
- **WHEN** a spec has `n_partitions: 50` (explicit integer)
- **THEN** the system SHALL return `n_partitions: 50` unchanged

#### Scenario: Missing target_file_size_mb uses global default
- **WHEN** a spec has `target_file_size_mb: null`
- **THEN** the system SHALL use the environment default (`DELTALAKE_TARGET_PARTITION_SIZE_MB`) for the computation
