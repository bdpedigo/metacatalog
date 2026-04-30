## MODIFIED Requirements

### Requirement: Table registration page
The UI SHALL provide a table registration page at `/ui/register` with a multi-step form: (1) URI entry and metadata preview, (2) column annotation and table metadata editing, (3) registration submission with result display.

#### Scenario: Registration page loads
- **WHEN** an authenticated user visits `/ui/register`
- **THEN** the system SHALL display a form with URI input field, datastack display (from global selector), and a Preview button

### Requirement: Metadata preview with diagnostic errors
The registration form SHALL provide a Preview button that triggers metadata discovery for the entered URI. On success, the form SHALL populate with discovered metadata (format, row count, column names and types). On failure, the form SHALL display diagnostic error messages distinguishing between URI unreachability, unrecognized format, and format-specific parse errors.

#### Scenario: Successful preview of a Delta table
- **WHEN** the user enters a valid Delta table URI and clicks Preview
- **THEN** the system SHALL call `POST /tables/preview` and display discovered metadata: format ("delta"), column names and types in a table, row count, Delta-specific metadata (delta version, partition columns)

#### Scenario: Successful preview of a Parquet file
- **WHEN** the user enters a valid Parquet file URI and clicks Preview
- **THEN** the system SHALL display discovered metadata: format ("parquet"), column names and types, row count, Parquet-specific metadata (row group count, compression)

#### Scenario: Preview fails — URI unreachable
- **WHEN** the user enters a URI that the catalog service cannot access
- **THEN** the system SHALL display a diagnostic error indicating the URI could not be reached, distinct from format errors

#### Scenario: Preview fails — format unrecognizable
- **WHEN** the user enters a URI that is reachable but cannot be identified as a known format (Delta, Parquet)
- **THEN** the system SHALL display a diagnostic error indicating the format could not be detected

#### Scenario: Preview fails — format-specific parse error
- **WHEN** the user enters a URI that is identified as Delta but the transaction log cannot be read
- **THEN** the system SHALL display a format-specific diagnostic error (e.g., "Delta: transaction log corrupt or unreadable")

### Requirement: Column annotation editing
After successful preview, the registration form SHALL display a column table with one row per discovered column. Each row SHALL show the column name (read-only), data type (read-only), a description text field (editable), and a kind section for setting column kinds.

#### Scenario: Column table populated from preview
- **WHEN** preview returns metadata with columns `[{name: "pt_root", dtype: "int64"}, {name: "score", dtype: "float64"}]`
- **THEN** the form SHALL display a table with two rows, each showing name, type, an empty description field, and a "Set Kind" button

#### Scenario: User enters column description
- **WHEN** the user types "Root ID of the neuron" into the description field for column "pt_root"
- **THEN** the value SHALL be included in the `column_annotations` payload when the form is submitted

### Requirement: Column kind builder with cascading dropdowns
The registration form SHALL provide a "Set Kind" interaction on each column row. Setting a kind SHALL present a kind selector with options: "Materialization", "Segmentation", "Packed Point", and "Split Point". Based on the selected kind, variant-specific fields SHALL appear:

- **Materialization**: a target table/view dropdown (populated from materialization service) and a target column dropdown (populated based on the selected target table/view).
- **Segmentation**: a node level dropdown with common presets ("Root ID", "Supervoxel ID", "Level 2 ID") and a "Custom level…" option that reveals a numeric input for entering arbitrary level numbers.
- **Packed Point**: an optional resolution input accepting three comma-separated float values (e.g., `4.0, 4.0, 40.0`).
- **Split Point**: a required axis selector ("X", "Y", "Z"), an optional point group text field, and an optional resolution input (single float value).

Only one kind SHALL be selectable per column. Changing the kind SHALL clear the variant-specific fields.

#### Scenario: Add materialization kind shows target table dropdown
- **WHEN** the user clicks "Set Kind" on a column row and selects "Materialization"
- **THEN** the system SHALL display a target table/view dropdown populated with available materialization tables and views for the current datastack

#### Scenario: Selecting target table populates column dropdown
- **WHEN** the user selects "synapses" from the target table dropdown
- **THEN** the system SHALL fetch the column schema for "synapses" and populate the target column dropdown with its column names

#### Scenario: Add segmentation kind shows node level selector
- **WHEN** the user clicks "Set Kind" on a column row and selects "Segmentation"
- **THEN** the system SHALL display a node level dropdown with common presets ("Root ID", "Supervoxel ID", "Level 2 ID") and a "Custom level…" option

#### Scenario: Segmentation custom level input
- **WHEN** the user selects "Custom level…" from the segmentation node level dropdown
- **THEN** the system SHALL reveal a numeric input where the user can enter an arbitrary level number (the system constructs `level{N}_id` from the entered number)

#### Scenario: Add packed point kind shows resolution field
- **WHEN** the user clicks "Set Kind" on a column row and selects "Packed Point"
- **THEN** the system SHALL display an optional resolution input accepting three comma-separated float values

#### Scenario: Add split point kind shows spatial fields
- **WHEN** the user clicks "Set Kind" on a column row and selects "Split Point"
- **THEN** the system SHALL display a required axis selector ("X", "Y", "Z"), an optional point group text field, and an optional resolution input (single float)

#### Scenario: Changing kind clears previous fields
- **WHEN** the user has selected "Materialization" and filled in target table/column, then switches to "Split Point"
- **THEN** the system SHALL clear the materialization fields and show the split point fields

#### Scenario: Remove a kind
- **WHEN** the user removes a kind from a column
- **THEN** the kind SHALL be removed from the form without a server round-trip

### Requirement: Incremental name validation
The registration form SHALL include a table name field. When the user finishes typing (on field blur), the system SHALL check name availability by verifying the name is not reserved by materialization and does not duplicate an existing asset. The result SHALL be displayed inline as a success or error indicator.

#### Scenario: Name is available
- **WHEN** the user enters "my_feature_table" in the name field and tabs away
- **THEN** the system SHALL check name availability and display a success indicator (e.g., ✓) next to the field

#### Scenario: Name is reserved by materialization
- **WHEN** the user enters "synapses" (a materialization table name) and tabs away
- **THEN** the system SHALL display an error indicator and message that the name is reserved

#### Scenario: Name duplicates existing asset
- **WHEN** the user enters a name that matches an existing asset in the same datastack (with same mat_version and revision)
- **THEN** the system SHALL display an error indicator and message that the name is already taken

### Requirement: Registration submission with result display
The registration form SHALL provide a Register button that submits the complete form (URI, name, mat_version, column annotations with kinds, and all user-settable asset fields) via `POST /tables/register`. On success, the system SHALL display the registered table's ID and details with options to view the table or register another. On failure, the system SHALL display validation errors on the form without losing the user's input.

The registration form SHALL expose all user-settable fields from the `TableRequest` schema, including: revision, mutability, maturity, is_managed, access_group, expires_at, and properties. Fields not on the form (auto-determined) are limited to: datastack (from global selector), asset_type (always "table"), and source (always "user"). A sync test SHALL enforce that any field added to `TableRequest` is either on the form or explicitly marked as auto-determined.

#### Scenario: Successful registration
- **WHEN** the user clicks Register with valid form data
- **THEN** the system SHALL submit to `POST /tables/register`, display a success message with the table ID, and offer "Register Another" action

#### Scenario: Registration fails with validation errors
- **WHEN** the user clicks Register but the server returns validation errors (e.g., URI no longer reachable, name now taken)
- **THEN** the system SHALL display the errors on the form with the user's input preserved, allowing them to fix and retry

#### Scenario: Re-extraction on register
- **WHEN** the user has previewed a table and then clicks Register some time later
- **THEN** the system SHALL re-extract metadata from the URI at registration time (not reuse preview results) to ensure freshness
