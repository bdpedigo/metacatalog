## MODIFIED Requirements

### Requirement: Column annotation submission at registration
The `POST /api/v1/tables/register` endpoint SHALL accept an optional `column_annotations` field in the request body. When provided, the annotations SHALL be validated (materialization kind targets checked against the materialization service; segmentation and point kinds validated by schema constraints only) and stored in the `column_annotations` JSONB field. When omitted, `column_annotations` SHALL be stored as an empty array.

#### Scenario: Registration with materialization kind
- **WHEN** a user registers a table with `column_annotations` including a description for column `id` and a materialization kind targeting `synapses.id`
- **THEN** the system SHALL validate the materialization kind target, store the annotations, and return the table with merged column view

#### Scenario: Registration with segmentation kind
- **WHEN** a user registers a table with `column_annotations` including a segmentation kind with `node_level: "root_id"` on column `pt_root_id`
- **THEN** the system SHALL accept the annotation without external validation and store it

#### Scenario: Registration with packed point kind
- **WHEN** a user registers a table with `column_annotations` including a packed point kind with optional `resolution: [4.0, 4.0, 40.0]` on column `pt_position`
- **THEN** the system SHALL accept the annotation without external validation and store it

#### Scenario: Registration with split point kind
- **WHEN** a user registers a table with `column_annotations` including a split point kind with `axis: "x"`, `point_group: "pt_position"` on column `pt_position_x`
- **THEN** the system SHALL accept the annotation without external validation and store it

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

### Requirement: Column kind validation at write time
When column annotations containing kinds are submitted (at registration or via annotation update), the system SHALL validate each kind based on its `kind` field. For `"materialization"` kinds, the system SHALL validate `target_table` and `target_column` against the materialization service. For `"segmentation"`, `"packed_point"`, and `"split_point"` kinds, validation SHALL be limited to schema/enum constraints (Pydantic validation). If a materialization kind references a non-existent table or column, the system SHALL reject the request with a 422 error indicating which kinds failed validation.

#### Scenario: Valid materialization kind
- **WHEN** a user submits a materialization kind referencing `synapses.id` and `synapses` exists in the materialization service with column `id`
- **THEN** the system SHALL accept the annotation

#### Scenario: Invalid materialization kind target table
- **WHEN** a user submits a materialization kind referencing `nonexistent_table.id`
- **THEN** the system SHALL return 422 with an error indicating the target table does not exist

#### Scenario: Invalid materialization kind target column
- **WHEN** a user submits a materialization kind referencing `synapses.nonexistent_column`
- **THEN** the system SHALL return 422 with an error indicating the target column does not exist in the target table

#### Scenario: Segmentation kind passes validation
- **WHEN** a user submits a segmentation kind with `node_level: "root_id"`
- **THEN** the system SHALL accept the annotation (no external service check)

#### Scenario: Packed point kind passes validation
- **WHEN** a user submits a packed point kind with `resolution: [4.0, 4.0, 40.0]`
- **THEN** the system SHALL accept the annotation (no external service check)

#### Scenario: Split point kind passes validation
- **WHEN** a user submits a split point kind with `axis: "z"`, `point_group: "position"`
- **THEN** the system SHALL accept the annotation (no external service check)
