## ADDED Requirements

### Requirement: Controlled asset_type vocabulary
The system SHALL enforce `asset_type` as a controlled enum. The initial allowed values SHALL be `"table"`. The system SHALL reject registration requests with an unrecognized `asset_type` with a 422 response.

#### Scenario: Valid asset_type accepted
- **WHEN** a registration request specifies `asset_type: "table"`
- **THEN** the system SHALL accept the value and proceed with validation

#### Scenario: Unknown asset_type rejected
- **WHEN** a registration request specifies `asset_type: "unknown_thing"`
- **THEN** the system SHALL return 422 with a message indicating the asset_type is not recognized

### Requirement: Controlled format vocabulary per asset_type
The system SHALL enforce `format` as a controlled enum scoped to the asset's `asset_type`. For `asset_type: "table"`, the allowed formats SHALL be `"parquet"`, `"delta"`, and `"lance"`. The system SHALL reject registration requests with an unrecognized `format` for the given `asset_type` with a 422 response.

#### Scenario: Valid format for table accepted
- **WHEN** a registration request specifies `asset_type: "table"` and `format: "delta"`
- **THEN** the system SHALL accept the value and proceed with validation

#### Scenario: Unknown format for table rejected
- **WHEN** a registration request specifies `asset_type: "table"` and `format: "csv"`
- **THEN** the system SHALL return 422 with a message indicating the format is not valid for asset_type "table"

### Requirement: Type-format combination registry
The system SHALL maintain a registry of valid `(asset_type, format)` combinations. Each combination SHALL map to a properties validation schema and a metadata extractor. The system SHALL reject registration requests for unregistered combinations with a 422 response.

#### Scenario: Registered combination accepted
- **WHEN** a registration request specifies `asset_type: "table"` and `format: "parquet"`
- **THEN** the system SHALL accept the combination and apply the corresponding validation schema and metadata extractor

#### Scenario: Hypothetical invalid combination rejected
- **WHEN** a future asset_type is added and a registration request specifies it with a format not registered for that type
- **THEN** the system SHALL return 422 indicating the combination is not valid

### Requirement: Type-specific properties validation
The system SHALL validate the `properties` field against a schema determined by the `(asset_type, format)` combination. For `asset_type: "table"`, all formats SHALL require a `description` field (string) in `properties`. The system SHALL reject registration requests where `properties` does not satisfy the type-specific schema with a 422 response.

#### Scenario: Table registration with description accepted
- **WHEN** a registration request specifies `asset_type: "table"` and `properties: { "description": "Synapse locations and partners" }`
- **THEN** the system SHALL accept the properties

#### Scenario: Table registration without description rejected
- **WHEN** a registration request specifies `asset_type: "table"` and `properties: {}` (no description)
- **THEN** the system SHALL return 422 with a message indicating that `description` is required for table assets

### Requirement: Dry-run validates type-specific rules
The validation endpoint (`POST /api/v1/assets/validate`) SHALL apply the same `asset_type`/`format` enum checks and type-specific properties validation as the registration endpoint. The validation report SHALL include a `type_validation` check with pass/fail status.

#### Scenario: Dry-run catches invalid format
- **WHEN** a user POSTs to `/api/v1/assets/validate` with `asset_type: "table"` and `format: "csv"`
- **THEN** the system SHALL return 200 with a validation report showing `type_validation: { passed: false, message: "..." }`
