## MODIFIED Requirements

### Requirement: Asset data model
The system SHALL store assets with the following required fields: `id` (UUID), `datastack` (string), `name` (string), `revision` (integer, default 1), `uri` (string), `asset_type` (string — polymorphic discriminator), `owner` (string), `is_managed` (boolean), `mutability` (enum: `"static"` or `"mutable"`), `maturity` (enum: `"stable"`, `"draft"`, or `"deprecated"`), `properties` (JSON object), and `created_at` (timestamp). The system SHALL also store optional fields: `expires_at` (timestamp) for TTL lifecycle and `access_group` (nullable string) for per-asset permissions. The `format` and `mat_version` fields are REMOVED from the base asset model — these are now part of the `tables` extension table. The `asset_type` column SHALL serve as the polymorphic discriminator for joined table inheritance. Uniqueness for table assets SHALL be enforced on the `tables` join: `(datastack, name, mat_version, revision)` where `mat_version IS NOT NULL`, and `(datastack, name, revision)` where `mat_version IS NULL`. Non-table assets SHALL enforce uniqueness via `(datastack, name, revision)` on the `assets` table.

#### Scenario: Unique constraint enforcement
- **WHEN** a registration request provides a `(datastack, name, mat_version, revision)` tuple that already exists
- **THEN** the system SHALL reject the request with a 409 Conflict response including the existing asset's ID

#### Scenario: Unique constraint with NULL mat_version
- **WHEN** two registration requests provide the same `(datastack, name, revision)` with `mat_version: null`
- **THEN** the system SHALL reject the second request with a 409 Conflict response

#### Scenario: Same name at different mat versions
- **WHEN** assets are registered with the same `(datastack, name, revision)` but different `mat_version` values
- **THEN** the system SHALL accept both registrations as distinct assets

#### Scenario: Optional expiry
- **WHEN** an asset is registered without an `expires_at` value
- **THEN** the system SHALL store the asset with a NULL `expires_at`, meaning it is retained indefinitely

#### Scenario: Non-table asset uniqueness
- **WHEN** a non-table asset is registered with `(datastack, name, revision)` matching an existing non-table asset
- **THEN** the system SHALL reject the request with a 409 Conflict response
