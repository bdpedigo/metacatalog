## MODIFIED Requirements

### Requirement: Column kind builder with cascading dropdowns
The registration form SHALL provide a "Set Kind" interaction on each column row. Setting a kind SHALL present a kind selector with options: "Materialization", "Segmentation", and "Point". Based on the selected kind, variant-specific fields SHALL appear:

- **Materialization**: a target table/view dropdown (populated from materialization service) and a target column dropdown (populated based on the selected target table/view).
- **Segmentation**: a node level input with common presets ("Root ID", "Supervoxel ID", "Level 2 ID") and support for entering arbitrary level numbers.
- **Point**: an optional axis selector ("X", "Y", "Z") and an optional point group text field.

Only one kind SHALL be selectable per column. Changing the kind SHALL clear the variant-specific fields.

#### Scenario: Add materialization kind shows target table dropdown
- **WHEN** the user clicks "Set Kind" on a column row and selects "Materialization"
- **THEN** the system SHALL display a target table/view dropdown populated with available materialization tables and views for the current datastack

#### Scenario: Selecting target table populates column dropdown
- **WHEN** the user selects "synapses" from the target table dropdown
- **THEN** the system SHALL fetch the column schema for "synapses" and populate the target column dropdown with its column names

#### Scenario: Add segmentation kind shows node level selector
- **WHEN** the user clicks "Set Kind" on a column row and selects "Segmentation"
- **THEN** the system SHALL display a node level input with common presets ("Root ID", "Supervoxel ID", "Level 2 ID") and the ability to enter an arbitrary level number

#### Scenario: Add point kind shows spatial fields
- **WHEN** the user clicks "Set Kind" on a column row and selects "Point"
- **THEN** the system SHALL display an optional axis selector and an optional point group text field

#### Scenario: Changing kind clears previous fields
- **WHEN** the user has selected "Materialization" and filled in target table/column, then switches to "Segmentation"
- **THEN** the system SHALL clear the materialization fields and show the segmentation node level selector

#### Scenario: Remove a kind
- **WHEN** the user removes a kind from a column
- **THEN** the kind SHALL be removed from the form without a server round-trip
