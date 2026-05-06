## ADDED Requirements

### Requirement: Wizard page rendering with datastack filtering
The system SHALL render a 3-step wizard UI at `/materialize/deltalake/` that displays only datastacks for which the authenticated user has `dataset_admin` permission. The wizard SHALL use the same Flask + Jinja2 + Alpine.js framework as the existing upload wizard.

#### Scenario: Admin user sees filtered datastacks
- **WHEN** a user with `dataset_admin` on `minnie65_phase3` navigates to the wizard
- **THEN** the system SHALL display `minnie65_phase3` in the datastack dropdown and exclude datastacks the user lacks admin permission for

#### Scenario: Non-admin user denied access
- **WHEN** a user without any `dataset_admin` permissions navigates to the wizard
- **THEN** the system SHALL redirect to a permission warning page

### Requirement: Step 1 — Table selection and global configuration
The system SHALL provide Step 1 with dropdown selectors for datastack, version, and table name. The version dropdown SHALL be populated from the existing versions endpoint and default to the latest version. The table dropdown SHALL be populated from the existing tables endpoint for the selected version. The system SHALL display a configurable `target_partition_size_mb` field defaulting to the environment value (`DELTALAKE_TARGET_PARTITION_SIZE_MB`). The system SHALL display the output bucket path as read-only informational text.

#### Scenario: Selecting a datastack populates versions
- **WHEN** the user selects a datastack
- **THEN** the system SHALL fetch available materialized versions and populate the version dropdown with the latest pre-selected

#### Scenario: Selecting a version populates tables
- **WHEN** the user selects a version
- **THEN** the system SHALL fetch the list of tables for that frozen version and populate the table dropdown

#### Scenario: Target partition size defaults from environment
- **WHEN** Step 1 loads
- **THEN** the `target_partition_size_mb` field SHALL display the server-side default value (from `DELTALAKE_TARGET_PARTITION_SIZE_MB`)

### Requirement: Step 1 — Discover specs trigger
The system SHALL provide a "Discover Specs" button that POSTs to the discover-specs endpoint with `{ datastack, version, table_name, target_partition_size_mb }`. While discovery runs, the UI SHALL display a loading spinner. On success, the UI SHALL navigate to Step 2 with the discovered specs.

#### Scenario: Successful spec discovery
- **WHEN** the user clicks "Discover Specs" with valid selections
- **THEN** the system SHALL POST to the discovery endpoint, show a spinner, and on success transition to Step 2 with the returned specs

#### Scenario: Discovery failure
- **WHEN** spec discovery fails (e.g., table not found in frozen DB)
- **THEN** the system SHALL display the error message and remain on Step 1

### Requirement: Step 2 — Spec review and editing
The system SHALL display each discovered `DeltaLakeOutputSpec` as an editable card showing: `partition_by`, `partition_strategy`, `n_partitions` (with override input), `target_file_size_mb` (optional override, inheriting from global), `zorder_columns`, `bloom_filter_columns`, and `source_geometry_column` (if spatial). The system SHALL also display table metadata (row count, estimated bytes/row) as read-only context.

#### Scenario: Viewing auto-discovered specs
- **WHEN** Step 2 loads after successful discovery
- **THEN** the system SHALL display one card per spec with all fields populated from discovery results

#### Scenario: Overriding n_partitions on a spec
- **WHEN** the user enters a numeric value in the n_partitions override field
- **THEN** the system SHALL store the override for that spec (replacing "auto")

#### Scenario: Overriding target_file_size_mb on a spec
- **WHEN** the user enters a value in the per-spec target_file_size_mb field
- **THEN** the system SHALL store the override for that spec

### Requirement: Step 2 — Recalculate partitions
The system SHALL provide a "Recalculate" button that POSTs the current specs (with any overrides) plus `row_count` and `bytes_per_row` to the recalculate endpoint. On success, the UI SHALL update each spec's `n_partitions` display with the recomputed values.

#### Scenario: Recalculate after changing target file size
- **WHEN** the user changes `target_file_size_mb` on a spec and clicks "Recalculate"
- **THEN** the system SHALL POST to the recalculate endpoint and update the displayed `n_partitions` for specs set to "auto"

### Requirement: Step 2 — Remove spec
The system SHALL allow the user to remove any spec from the list. At least one spec MUST remain.

#### Scenario: Removing a spec
- **WHEN** the user clicks "Remove" on a spec card and more than one spec exists
- **THEN** the system SHALL remove that spec from the list

#### Scenario: Preventing removal of last spec
- **WHEN** only one spec remains and the user attempts to remove it
- **THEN** the system SHALL prevent removal and display a message that at least one spec is required

### Requirement: Step 3 — Confirmation and launch
The system SHALL display a summary of the export configuration (datastack, version, table, all specs with final partition counts, target URIs) and a "Launch Export" button. On launch, the system SHALL POST to the existing export endpoint with the configured specs and `target_partition_size_mb`, then redirect to the monitoring page.

#### Scenario: Successful launch
- **WHEN** the user clicks "Launch Export"
- **THEN** the system SHALL POST the final configuration to the export endpoint and redirect to the monitoring page

#### Scenario: Export already exists error
- **WHEN** the export endpoint returns an error (e.g., Delta Lake already exists at target URI)
- **THEN** the system SHALL display the error message on Step 3 without redirecting

### Requirement: Wizard state persistence via localStorage
The system SHALL persist wizard state (selected datastack, version, table, target_partition_size_mb, discovered specs with edits) in localStorage across step navigation and page refreshes. The state SHALL be cleared on successful export launch.

#### Scenario: Page refresh preserves state
- **WHEN** the user refreshes the browser on Step 2
- **THEN** the system SHALL restore the wizard state from localStorage including discovered specs

#### Scenario: State cleared after launch
- **WHEN** an export is successfully launched
- **THEN** the system SHALL clear the wizard localStorage state
