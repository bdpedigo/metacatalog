## ADDED Requirements

### Requirement: Column annotation submission at registration
The `POST /api/v1/tables/register` endpoint SHALL accept an optional `column_annotations` field in the request body. When provided, the annotations SHALL be validated (column link targets checked against the materialization service) and stored in the `column_annotations` JSONB field. When omitted, `column_annotations` SHALL be stored as an empty array.

#### Scenario: Registration with annotations
- **WHEN** a user registers a table with `column_annotations` including a description for column `id` and a link to `synapses.id`
- **THEN** the system SHALL validate the link target, store the annotations, and return the table with merged column view

#### Scenario: Registration without annotations
- **WHEN** a user registers a table without providing `column_annotations`
- **THEN** the system SHALL store an empty array for `column_annotations`

### Requirement: Column annotation update with replace semantics
The system SHALL provide `PATCH /api/v1/tables/{id}/annotations` accepting a `column_annotations` array in the request body. The provided array SHALL replace the existing `column_annotations` value entirely. The caller MUST have write permission on the table's datastack.

#### Scenario: Replace annotations
- **WHEN** an authorized user PATCHes annotations for a table, providing a complete annotations array
- **THEN** the system SHALL replace the stored `column_annotations` with the provided array and return the updated table

#### Scenario: Clear all annotations
- **WHEN** an authorized user PATCHes annotations with an empty array
- **THEN** the system SHALL store an empty array, effectively removing all annotations

#### Scenario: Unauthorized annotation update
- **WHEN** a user without write permission attempts to update annotations
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Column link validation at write time
When column annotations containing links are submitted (at registration or via annotation update), the system SHALL validate each link's `target_table` and `target_column` against the materialization service for the target datastack. If a referenced table or column does not exist, the system SHALL reject the request with a 422 error indicating which links failed validation.

#### Scenario: Valid column link
- **WHEN** a user submits a column link referencing `synapses.id` and `synapses` exists in the materialization service with column `id`
- **THEN** the system SHALL accept the annotation

#### Scenario: Invalid column link target table
- **WHEN** a user submits a column link referencing `nonexistent_table.id`
- **THEN** the system SHALL return 422 with an error indicating the target table does not exist

#### Scenario: Invalid column link target column
- **WHEN** a user submits a column link referencing `synapses.nonexistent_column`
- **THEN** the system SHALL return 422 with an error indicating the target column does not exist in the target table
