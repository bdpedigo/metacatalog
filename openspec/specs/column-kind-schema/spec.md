## ADDED Requirements

### Requirement: Discriminated union kind schema
The system SHALL represent column kinds as a discriminated union keyed on the `kind` field. The valid `kind` values SHALL be `"materialization"`, `"segmentation"`, `"packed_point"`, and `"split_point"`. Each variant SHALL carry only its own fields; no shared optional fields.

#### Scenario: Materialization kind
- **WHEN** a column kind has `kind: "materialization"`
- **THEN** the kind SHALL require `target_table` (string) and `target_column` (string) fields

#### Scenario: Segmentation kind
- **WHEN** a column kind has `kind: "segmentation"`
- **THEN** the kind SHALL require a `node_level` string field matching one of: `"root_id"`, `"supervoxel_id"`, or the pattern `level{N}_id` where N is a positive integer (e.g., `"level2_id"`, `"level4_id"`)

#### Scenario: Packed point kind
- **WHEN** a column kind has `kind: "packed_point"`
- **THEN** the kind SHALL optionally accept `resolution` (a list of exactly 3 floats `[rx, ry, rz]` or null)

#### Scenario: Split point kind
- **WHEN** a column kind has `kind: "split_point"`
- **THEN** the kind SHALL require `axis` (`"x"`, `"y"`, or `"z"`) and optionally accept `point_group` (string or null) and `resolution` (float or null)

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
When `kind` is `"split_point"`, the optional `point_group` field SHALL allow grouping related spatial columns (e.g., x, y, z columns sharing the same prefix). Columns with the same `point_group` value within a table are considered part of the same spatial point.

#### Scenario: Grouped spatial columns
- **WHEN** three columns are annotated with split point kinds having `point_group: "pt_position"` and axes `"x"`, `"y"`, `"z"` respectively
- **THEN** the system SHALL store all three annotations and consumers MAY identify them as a single spatial point

#### Scenario: Packed spatial column
- **WHEN** a column is annotated with a packed point kind (`kind: "packed_point"`)
- **THEN** the system SHALL accept the annotation (all xyz coordinates are in one field; no axis or point_group needed)

### Requirement: Point group uniqueness validation
The system SHALL validate that no two `split_point` annotations within the same table share the same `(point_group, axis)` combination when `point_group` is non-null.

#### Scenario: Duplicate point_group + axis rejected
- **WHEN** two columns in the same table both have `kind: "split_point"`, `point_group: "pt_position"`, `axis: "x"`
- **THEN** the system SHALL return 422 with an error indicating the duplicate

#### Scenario: Same axis with different point_groups allowed
- **WHEN** two columns have `kind: "split_point"`, `axis: "x"` but different `point_group` values
- **THEN** the system SHALL accept both annotations

### Requirement: Resolution fields on point kinds
Point kinds optionally carry resolution metadata describing the spatial resolution of the coordinates.

#### Scenario: Packed point resolution
- **WHEN** a packed point kind includes `resolution: [4.0, 4.0, 40.0]`
- **THEN** the system SHALL validate it is a list of exactly 3 floats and store it

#### Scenario: Packed point resolution wrong length
- **WHEN** a packed point kind includes `resolution: [4.0, 4.0]`
- **THEN** the system SHALL return 422 with an error indicating resolution must be exactly 3 values

#### Scenario: Split point resolution
- **WHEN** a split point kind includes `resolution: 4.0`
- **THEN** the system SHALL store the scalar float value

#### Scenario: Resolution omitted
- **WHEN** a point kind (packed or split) omits the `resolution` field
- **THEN** the system SHALL store `resolution: null`

### Requirement: Validation dispatches on kind
The system SHALL validate column kinds differently based on `kind`:
- `"materialization"`: validate `target_table` existence against the materialization service
- `"segmentation"`: validate `node_level` matches pattern (`root_id`, `supervoxel_id`, or `level{N}_id`); no external service call
- `"packed_point"` / `"split_point"`: validated by Pydantic schema constraints; no external service call

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

#### Scenario: Point kinds require no external validation
- **WHEN** a packed_point or split_point kind is submitted
- **THEN** the system SHALL accept the kind without contacting any external service (axis is enum-constrained, resolution is type-checked by Pydantic)
