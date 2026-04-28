## MODIFIED Requirements

### Requirement: Materialization table name reservation
The system SHALL check asset names at registration time against the set of materialization table names for the same datastack (queried from the MaterializationEngine `/tables` endpoint across all versions). If the name matches a materialization table, the system SHALL reject the registration unless the caller has admin/service-level write permission and sets `properties.source` to `"materialization"`. Layout variants (names matching `{mat_table}.{suffix}`) SHALL also be reserved. The dry-run validation endpoint SHALL also perform this check. The name reservation check SHALL also be available as an independent endpoint (`GET /api/v1/assets/check-name`) that additionally checks for duplicate assets with the same `(datastack, name, mat_version, revision)` tuple, returning a combined availability result.

#### Scenario: Regular user blocked from registering a mat table name
- **WHEN** a regular user attempts to register an asset named `synapses` in a datastack where `synapses` exists as a materialization table
- **THEN** the system SHALL return 409 with a message indicating the name is reserved for materialization

#### Scenario: Mat service registers a mat table name
- **WHEN** a caller with admin/service write permission registers an asset named `synapses` with `properties.source: "materialization"`
- **THEN** the system SHALL accept the registration

#### Scenario: Layout variant of a reserved name is also reserved
- **WHEN** a regular user attempts to register an asset named `synapses.by_pre_root` and `synapses` exists as a materialization table
- **THEN** the system SHALL return 409 with a message indicating the name is reserved (layout variants of mat table names are reserved)

#### Scenario: Independent name availability check — name available
- **WHEN** a user requests `GET /api/v1/assets/check-name?datastack=X&name=Y`
- **AND** the name is not reserved by materialization and no duplicate asset exists
- **THEN** the system SHALL return 200 with `{available: true}`

#### Scenario: Independent name availability check — name taken
- **WHEN** a user requests `GET /api/v1/assets/check-name?datastack=X&name=Y&mat_version=1&revision=0`
- **AND** an asset with that `(datastack, name, mat_version, revision)` tuple already exists
- **THEN** the system SHALL return 200 with `{available: false, reason: "duplicate", existing_id: "..."}` 

#### Scenario: Independent name availability check — name reserved
- **WHEN** a user requests `GET /api/v1/assets/check-name?datastack=X&name=synapses`
- **AND** `synapses` is a materialization table in that datastack
- **THEN** the system SHALL return 200 with `{available: false, reason: "reserved"}`
