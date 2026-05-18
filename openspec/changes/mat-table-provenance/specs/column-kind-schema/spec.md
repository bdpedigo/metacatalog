## MODIFIED Requirements

### Requirement: Discriminated union kind schema
The system SHALL represent column kinds as a discriminated union keyed on the `kind` field. The valid `kind` values SHALL be `"segmentation"`, `"packed_point"`, and `"split_point"`. Each variant SHALL carry only its own fields; no shared optional fields.

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

### Requirement: Validation dispatches on kind
The system SHALL validate column kinds differently based on `kind`:
- `"segmentation"`: validate `node_level` matches pattern (`root_id`, `supervoxel_id`, or `level{N}_id`); no external service call
- `"packed_point"` / `"split_point"`: validated by Pydantic schema constraints; no external service call

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

## REMOVED Requirements

### Requirement: Materialization kind
**Reason**: Column origin (where a value came from) is not a semantic type. Encoding it as a `kind` conflates provenance with semantics, making it impossible to express both the semantic type and origin of a column simultaneously. Column provenance is now expressed via the `links` field on `ColumnAnnotation`.
**Migration**: Any existing `kind: "materialization"` annotations should be migrated to a `ColumnLink` with `link_type: "copy"` and equivalent `target_table` / `target_column` values.

## ADDED Requirements

### Requirement: Column links on ColumnAnnotation
Each `ColumnAnnotation` SHALL carry a `links` field containing a list of `ColumnLink` objects (empty list by default). A `ColumnLink` encodes a relationship between the annotated column and a column in a materialization table within the same datastack.

A `ColumnLink` SHALL have the following fields:
- `link_type` (string, required) — `"copy"` or `"join"`. `"copy"` means value-equivalent: the values in this column are the same as the target, so routing can substitute the static dump for a live mat query. `"copy"` also implies a valid join. `"join"` means a join is valid but values are not a direct copy (e.g., a foreign key in an enriched table).
- `target_table` (string, required) — the materialization table name within the same datastack.
- `target_column` (string or null) — the specific column in the target table, or null for computed/merged columns with no 1:1 source column.

#### Scenario: Column with a copy link
- **WHEN** a column annotation for `root_id` includes a link with `link_type: "copy"`, `target_table: "synapses"`, `target_column: "root_id"`
- **THEN** the system SHALL store the link and consumers MAY use it to identify this column as value-equivalent to `synapses.root_id` and treat it as a valid join target

#### Scenario: Column with a join link
- **WHEN** a column annotation for `synapse_id` includes a link with `link_type: "join"`, `target_table: "synapses"`, `target_column: "id"`
- **THEN** the system SHALL store the link indicating a join from this column to `synapses.id` is valid, but values are not a direct copy

#### Scenario: Column with null target_column
- **WHEN** a column annotation includes a link with `target_column: null`
- **THEN** the system SHALL store the link, indicating the column is related to the target table but has no 1:1 source column (e.g., a packed point computed from multiple source columns)

#### Scenario: Invalid link_type rejected
- **WHEN** a column annotation includes a link with `link_type: "derived_from"` or any value outside `"copy"` and `"join"`
- **THEN** the system SHALL return 422 with an error indicating the invalid link_type

#### Scenario: Column with no links
- **WHEN** a column annotation omits the `links` field or provides an empty array
- **THEN** the system SHALL store an empty links array for that column
