## ADDED Requirements

### Requirement: Asset edit page
The UI SHALL render an edit page at `/ui/explore/{id}/edit` for modifying mutable asset fields. The page SHALL include a "Back to {asset_name}" link returning to the detail page. Only mutable fields SHALL be presented as form controls. Immutable fields (name, uri, format, datastack, mat_version, revision, asset_type, owner, is_managed, mutability, source, created_at) SHALL NOT be editable.

#### Scenario: User navigates to edit page
- **WHEN** a user clicks "Edit" on the detail page for asset "synapse_table"
- **THEN** the system SHALL display the edit form at `/ui/explore/{id}/edit` with editable controls for mutable fields

#### Scenario: Unauthorized user cannot edit
- **WHEN** a user without edit permission on the datastack navigates to `/ui/explore/{id}/edit`
- **THEN** the system SHALL return a 403 error or redirect to the detail page with an error message

### Requirement: Maturity editing
The edit page SHALL display radio buttons for the `maturity` field with options: stable, draft, deprecated. The current value SHALL be pre-selected.

#### Scenario: User changes maturity
- **WHEN** a user selects "deprecated" for an asset currently marked "stable"
- **AND** clicks "Save changes"
- **THEN** the system SHALL update the asset's maturity to "deprecated" via `PATCH /api/v1/assets/{id}` and redirect to the detail page

### Requirement: Access group editing
The edit page SHALL display a text input for `access_group`. The current value SHALL be pre-filled (or empty if NULL).

#### Scenario: User sets access group
- **WHEN** a user enters "team-alpha" in the access_group field and saves
- **THEN** the system SHALL update the asset's access_group to "team-alpha"

### Requirement: Expiry editing
The edit page SHALL display a date input for `expires_at`. The current value SHALL be pre-filled. Leaving the field blank SHALL set expires_at to NULL (no expiry).

#### Scenario: User sets expiry
- **WHEN** a user sets expires_at to "2026-12-31" and saves
- **THEN** the system SHALL update the asset's expires_at to that datetime

#### Scenario: User clears expiry
- **WHEN** a user clears the expires_at field (blank) and saves
- **THEN** the system SHALL set expires_at to NULL (asset retained indefinitely)

### Requirement: Column annotation editing for tables
The edit page for table assets SHALL display the column annotation editor (reusing the same annotation builder component from the registration page). The editor SHALL pre-populate with existing annotations. Saving SHALL call `PATCH /api/v1/tables/{id}/annotations` with the full replacement annotation set.

#### Scenario: User edits column description
- **WHEN** a user modifies the description for column "pre_pt_root_id" from "Pre-syn neuron" to "Presynaptic neuron root ID" and saves
- **THEN** the system SHALL send the full updated annotations array via PATCH and redirect to the detail page

#### Scenario: User adds a link to a column
- **WHEN** a user adds a link `{link_type: "foreign_key", target_table: "nucleus_detection_v0", target_column: "pt_root_id"}` to column "pre_pt_root_id" and saves
- **THEN** the system SHALL include the new link in the annotations PATCH request

### Requirement: Save confirmation and error handling
On successful save, the UI SHALL redirect the user to the asset detail page with the updated values visible. On error (e.g., validation failure, permission denied), the UI SHALL display the error message on the edit form without losing the user's input.

#### Scenario: Successful save redirect
- **WHEN** a user saves valid changes on the edit page
- **THEN** the system SHALL redirect to `/ui/explore/{id}` showing the updated values

#### Scenario: Save error preserves input
- **WHEN** a user submits invalid data (e.g., malformed expires_at)
- **THEN** the system SHALL re-render the edit form with an error message and the user's previously entered values intact
