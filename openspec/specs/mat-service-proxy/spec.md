## ADDED Requirements

### Requirement: Materialization table list proxy
The catalog service SHALL provide a route handler that returns the list of materialization tables for a given datastack and version. The handler SHALL query the materialization engine via CAVEclient using a service token. Results SHALL be cached with a TTL.

#### Scenario: Fetch table list for datastack
- **WHEN** the UI requests the list of materialization tables for datastack "minnie65_phase3"
- **THEN** the system SHALL return a list of table names from the materialization engine

#### Scenario: Cached response on repeat request
- **WHEN** the UI requests the same table list within the TTL window
- **THEN** the system SHALL return the cached result without querying the materialization engine again

#### Scenario: Materialization engine unreachable
- **WHEN** the materialization engine is unreachable or returns an error
- **THEN** the system SHALL return an appropriate error message to the UI

### Requirement: Materialization view list proxy
The catalog service SHALL provide a route handler that returns the list of materialization views for a given datastack and version. The handler SHALL query the materialization engine via CAVEclient using a service token. Results SHALL be cached with a TTL.

#### Scenario: Fetch view list for datastack
- **WHEN** the UI requests the list of materialization views for datastack "minnie65_phase3"
- **THEN** the system SHALL return a list of view names from the materialization engine

### Requirement: Unified linkable targets list
The catalog service SHALL provide a route handler that returns a combined list of materialization tables and views as potential column link targets. Each entry SHALL indicate whether it is a table or a view.

#### Scenario: Combined table and view list
- **WHEN** the UI requests linkable targets for a datastack
- **THEN** the system SHALL return a combined list including both tables (from `get_tables()`) and views (from `get_views()`), each annotated with its type

### Requirement: Column schema proxy for tables
The catalog service SHALL provide a route handler that returns the column names and types for a given materialization table. For tables, the handler SHALL resolve the schema type (via `get_table_metadata()`) and then resolve columns (via `schema_definition()` and column parsing). Results SHALL be cached with a TTL.

#### Scenario: Fetch columns for a materialization table
- **WHEN** the UI requests columns for materialization table "synapses"
- **THEN** the system SHALL return a list of column names with their types, including expanded spatial point columns (e.g., `pre_pt_root_id`, `pre_pt_position_x`)

#### Scenario: Cached column schema
- **WHEN** the UI requests columns for the same table within the TTL window
- **THEN** the system SHALL return the cached result

### Requirement: Column schema proxy for views
The catalog service SHALL provide a route handler that returns the column names and types for a given materialization view. For views, the handler SHALL use the direct view schema endpoint.

#### Scenario: Fetch columns for a materialization view
- **WHEN** the UI requests columns for materialization view "synapse_with_nucleus"
- **THEN** the system SHALL return a list of column names with their types

### Requirement: CAVEclient integration with service token
The catalog service SHALL initialize CAVEclient instances using a configured service token (`CAVE_TOKEN` environment variable) for materialization engine queries. CAVEclient calls SHALL be executed via `asyncio.to_thread` to avoid blocking the async event loop.

#### Scenario: Service token used for mat queries
- **WHEN** the catalog queries the materialization engine for table or column data
- **THEN** the query SHALL authenticate using the service token, not the requesting user's token

#### Scenario: Service token not configured
- **WHEN** `CAVE_TOKEN` is not set and a mat proxy request is made
- **THEN** the system SHALL return an error indicating the service is not configured for materialization queries

### Requirement: TTL cache for materialization reference data
The catalog service SHALL cache materialization reference data (table lists, view lists, column schemas) in-process with a configurable TTL (default 5 minutes). The cache SHALL be keyed by `(datastack, mat_version)` for lists and `(datastack, mat_version, target_name)` for column schemas.

#### Scenario: Cache expires after TTL
- **WHEN** the TTL has elapsed since the last cache population for a given key
- **AND** a new request is made for that key
- **THEN** the system SHALL query the materialization engine afresh and update the cache
