## MODIFIED Requirements

### Requirement: Delta Lake export progress endpoint
The existing `GET /materialize/run/write_deltalake/datastack/<name>/version/<version>/table_name/<table>/` SHALL return an extended JSON payload including `phase` (string), `error` (string or null), and `log_entries` (array of strings) in addition to the existing `status`, `rows_processed`, `total_rows`, `percent_complete`, and `last_updated` fields.

#### Scenario: Progress response includes phase and logs
- **WHEN** an authorized admin GETs progress for an active export
- **THEN** the system SHALL return `{ status, phase, rows_processed, total_rows, percent_complete, error, log_entries, last_updated }`

#### Scenario: Failed export includes error message
- **WHEN** an export has failed
- **THEN** the system SHALL return `status: "failed"` with `error` containing the Python exception message string

#### Scenario: Log entries are capped
- **WHEN** the export has produced more than 100 log messages
- **THEN** the system SHALL return only the most recent 100 entries in `log_entries`

## ADDED Requirements

### Requirement: Per-spec target_file_size_mb in export request
The existing `POST /materialize/run/write_deltalake/...` endpoint SHALL accept `target_file_size_mb` as an optional field within each `output_specs` entry. When provided, the export task SHALL use the per-spec value for partition count resolution instead of the global `DELTALAKE_TARGET_PARTITION_SIZE_MB`. When absent or null, the global value SHALL be used.

#### Scenario: Per-spec file size override
- **WHEN** an export is launched with a spec containing `target_file_size_mb: 128`
- **THEN** the export task SHALL resolve `n_partitions` for that spec using 128 MB as the target

#### Scenario: Null target_file_size_mb uses global
- **WHEN** an export is launched with a spec containing `target_file_size_mb: null`
- **THEN** the export task SHALL resolve `n_partitions` using the environment default

### Requirement: Export task writes phase transitions to Redis log
The export Celery task SHALL append phase-transition messages to a capped Redis list at key `deltalake_log:{datastack}:v{version}:{table}`. Messages SHALL be appended via `RPUSH` and the list SHALL be trimmed to 100 entries via `LTRIM`. The progress GET endpoint SHALL read this list and include it as `log_entries` in the response.

#### Scenario: Phase transition logged
- **WHEN** the export task transitions from `computing_boundaries` to `streaming`
- **THEN** the system SHALL append a timestamped message to the Redis log list

#### Scenario: Log list capped at 100
- **WHEN** more than 100 messages have been appended
- **THEN** the Redis list SHALL contain only the most recent 100 entries
