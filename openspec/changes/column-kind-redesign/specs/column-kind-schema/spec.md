## ADDED Requirements

### Requirement: Discriminated union kind schema
The system SHALL represent column kinds as a discriminated union keyed on the `kind` field. The valid `kind` values SHALL be `"materialization"`, `"segmentation"`, and `"point"`. Each variant SHALL carry only its own fields; no shared optional fields.

#### Scenario: Materialization kind
- **WHEN** a column kind has `kind: "materialization"`
- **THEN** the kind SHALL require `target_table` (string) and `target_column` (string) fields

#### Scenario: Segmentation kind
- **WHEN** a column kind has `kind: "segmentation"`
- **THEN** the kind SHALL require a `node_level` string field matching one of: `"root_id"`, `"supervoxel_id"`, or the pattern `level{N}_id` where N is a positive integer (e.g., `"level2_id"`, `"level4_id"`)

#### Scenario: Point kind
- **WHEN** a column kind has `kind: "point"`
- **THEN** the kind SHALL optionally accept `axis` (`"x"`, `"y"`, or `"z"`) and `point_group` (string)

#### Scenario: Invalid kind rejected
- **WHEN** a column kind is submitted with a `kind` value not in the valid set
- **THEN** the system SHALL return 422 with an error indicating the invalid kind

### Requirement: Singular kind per column annotation
Each `ColumnAnnotation` SHALL have at most one kind, represented as `kind: ColumnKind | None`. A column SHALL NOT carry multiple kinds simultaneously.

#### Scenario: Column with one kind
- **WHEN** a column annotation is submitted with a single kind object
- **THEN** the system SHALL store the kind on that column annotation

#### Scenario: Column with no kind
- **WHEN** a column annotation is submitted with `kind: null` or the `kind` field omitted
- **THEN** the system SHALL store no kind for that column annotation

### Requirement: Point group for spatial column grouping
When `kind` is `"point"`, the optional `point_group` field SHALL allow grouping related spatial columns (e.g., x, y, z columns sharing the same prefix). Columns with the same `point_group` value within a table are considered part of the same spatial point.

#### Scenario: Grouped spatial columns
- **WHEN** three columns are annotated with point kinds having `point_group: "pt_position"` and axes `"x"`, `"y"`, `"z"` respectively
- **THEN** the system SHALL store all three annotations and consumers MAY identify them as a single spatial point

#### Scenario: Packed spatial column without axis
- **WHEN** a column is annotated with a point kind having no `axis` field
- **THEN** the system SHALL accept the annotation (axis is optional, indicating a packed coordinate column)

### Requirement: Validation dispatches on kind
The system SHALL validate column kinds differently based on `kind`:
- `"materialization"`: validate `target_table` existence against the materialization service
- `"segmentation"`: validate `node_level` matches pattern (`root_id`, `supervoxel_id`, or `level{N}_id`); no external service call
- `"point"`: no external validation (axis is enum-constrained)

#### Scenario: Materialization kind validated against ME
- **WHEN** a materialization kind references `target_table: "synapses"`
- **THEN** the system SHALL check that `synapses` exists in the materialization service for the asset's datastack

#### Scenario: Segmentation kind with well-known alias
- **WHEN** a segmentation kind is submitted with `node_level: "root_id"`
- **THEN** the system SHALL accept the kind without contacting any external service

#### Scenario: Segmentation kind with numeric level
- **WHEN** a segmentation kind is submitted with `node_level: "level4_id"`
- **THEN** the system SHALL accept the kind (matches `level{N}_id` pattern)

#### Scenario: Segmentation kind with invalid node_level
- **WHEN** a segmentation kind is submitted with `node_level: "something_else"`
- **THEN** the system SHALL return 422 with an error indicating the invalid node_level

#### Scenario: Point kind requires no external validation
- **WHEN** a point kind is submitted with `axis: "x"`
- **THEN** the system SHALL accept the kind without contacting any external service
