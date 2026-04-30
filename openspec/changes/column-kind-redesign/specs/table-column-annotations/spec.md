## MODIFIED Requirements

### Requirement: Column annotation submission at registration
The `POST /api/v1/tables/register` endpoint SHALL accept an optional `column_annotations` field in the request body. When provided, the annotations SHALL be validated (materialization kind targets checked against the materialization service; segmentation and point kinds validated by enum constraints only) and stored in the `column_annotations` JSONB field. When omitted, `column_annotations` SHALL be stored as an empty array.

#### Scenario: Registration with materialization kind
- **WHEN** a user registers a table with `column_annotations` including a description for column `id` and a materialization kind targeting `synapses.id`
- **THEN** the system SHALL validate the materialization kind target, store the annotations, and return the table with merged column view

#### Scenario: Registration with segmentation kind
- **WHEN** a user registers a table with `column_annotations` including a segmentation kind with `node_level: "root_id"` on column `pt_root_id`
- **THEN** the system SHALL accept the annotation without external validation and store it

#### Scenario: Registration with point kind
- **WHEN** a user registers a table with `column_annotations` including a point kind with `axis: "x"`, `point_group: "pt_position"` on column `pt_position_x`
- **THEN** the system SHALL accept the annotation without external validation and store it

#### Scenario: Registration without annotations
- **WHEN** a user registers a table without providing `column_annotations`
- **THEN** the system SHALL store an empty array for `column_annotations`

### Requirement: Column kind validation at write time
When column annotations containing kinds are submitted (at registration or via annotation update), the system SHALL validate each kind based on its `kind` field. For `"materialization"` kinds, the system SHALL validate `target_table` and `target_column` against the materialization service. For `"segmentation"` and `"point"` kinds, validation SHALL be limited to schema/enum constraints. If a materialization kind references a non-existent table or column, the system SHALL reject the request with a 422 error indicating which kinds failed validation.

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

#### Scenario: Point kind passes validation
- **WHEN** a user submits a point kind with `axis: "z"`
- **THEN** the system SHALL accept the annotation (no external service check)
