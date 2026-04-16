## ADDED Requirements

### Requirement: Asset columns data model
The system SHALL store per-column metadata for table-type assets in an `asset_columns` table with the following fields: `asset_id` (UUID, foreign key to `assets.id` with ON DELETE CASCADE), `column_name` (text), `column_type` (text), `nullable` (boolean), `ordinal` (integer, position in schema), `description` (nullable text), `semantic_type` (nullable text), `unit` (nullable text), `ref_table` (nullable text), `ref_column` (nullable text), `ref_datastack` (nullable text), `ref_relationship` (nullable text, one of `"foreign_key"`, `"derived"`, `"lookup"`). The primary key SHALL be `(asset_id, column_name)`.

#### Scenario: Column metadata stored at registration
- **WHEN** a table asset is successfully registered and metadata extraction yields 5 columns
- **THEN** the system SHALL create 5 rows in `asset_columns` with the derived `column_name`, `column_type`, `nullable`, and `ordinal` fields populated

#### Scenario: Columns deleted with asset
- **WHEN** an asset is deleted via `DELETE /api/v1/assets/{id}`
- **THEN** the system SHALL cascade-delete all associated `asset_columns` rows

### Requirement: Column annotations at registration
The system SHALL accept an optional `column_annotations` field in the registration request body for table-type assets. `column_annotations` SHALL be a dictionary keyed by column name, where each value is an object with optional fields: `description` (string), `semantic_type` (string), `unit` (string), and `references` (object with `table`, `column`, and optional `datastack` and `relationship` fields).

#### Scenario: Registration with column annotations
- **WHEN** a registration request includes `column_annotations: { "pre_pt_root_id": { "description": "Root ID of the presynaptic neuron", "references": { "table": "nucleus_detection_v0", "column": "pt_root_id", "relationship": "lookup" } } }`
- **THEN** the system SHALL merge the declared annotations into the derived column metadata and store the result in `asset_columns`

#### Scenario: Annotation for nonexistent column warns
- **WHEN** a registration request includes a column annotation for column name `"foo"` but the extracted schema does not contain a column named `"foo"`
- **THEN** the system SHALL include a warning in the validation report indicating that `"foo"` does not exist in the extracted schema, and SHALL NOT create a row in `asset_columns` for `"foo"`

#### Scenario: Registration without column annotations
- **WHEN** a registration request for a table asset omits `column_annotations`
- **THEN** the system SHALL still populate `asset_columns` with derived column info (name, type, nullable, ordinal) and leave declared fields (description, semantic_type, unit, ref_*) as NULL

### Requirement: Column metadata in asset responses
The system SHALL include column metadata in asset responses for table-type assets. The `GET /api/v1/assets/{id}` and `GET /api/v1/assets/` responses SHALL include a `columns` field containing the list of column records when the asset has associated `asset_columns` rows.

#### Scenario: Get asset includes columns
- **WHEN** an authorized user GETs `/api/v1/assets/{id}` for a table asset with 10 columns
- **THEN** the response SHALL include a `columns` field with 10 column objects, each containing `column_name`, `column_type`, `nullable`, `ordinal`, and any declared annotations

#### Scenario: Non-table asset has no columns
- **WHEN** an authorized user GETs `/api/v1/assets/{id}` for a future non-table asset
- **THEN** the response SHALL include `columns: null` or omit the `columns` field

### Requirement: Soft enforcement of reference annotations for mat-sourced tables
The system SHALL include a warning in the validation report when a mat-sourced table (`properties.source: "materialization"`) has columns whose names end in `_root_id` and no `references` annotation is declared for those columns. This warning SHALL NOT block registration.

#### Scenario: Missing reference annotation triggers warning
- **WHEN** a registration request has `properties.source: "materialization"` and the extracted schema contains a column `pre_pt_root_id` with no corresponding `references` in `column_annotations`
- **THEN** the validation report SHALL include a warning: `column_annotation_warnings: [{ "column": "pre_pt_root_id", "message": "Column ending in _root_id has no references annotation" }]`

#### Scenario: Provided reference annotation suppresses warning
- **WHEN** a registration request has `properties.source: "materialization"` and `column_annotations` includes a `references` entry for `pre_pt_root_id`
- **THEN** the validation report SHALL NOT include a warning for that column
