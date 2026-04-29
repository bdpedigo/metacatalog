## MODIFIED Requirements

### Requirement: Asset listing with filters
The system SHALL accept asset listing via `GET /api/v1/assets/` with the following query parameters: `datastack` (required), `name` (exact match, optional), `mat_version` (exact match, optional), `revision` (exact match, optional), `format` (exact match, optional), `asset_type` (exact match, optional), `mutability` (exact match, optional), `maturity` (exact match, optional), `name_contains` (substring match via case-insensitive ILIKE, optional), `limit` (integer ≥1, max 1000, optional — when omitted all results are returned), `offset` (integer ≥0, default 0, optional), `sort_by` (field name, default "name", optional), and `sort_order` ("asc" or "desc", default "asc", optional). Expired assets (where `expires_at` is in the past) SHALL be excluded. When `limit` is provided, the response SHALL include an `X-Total-Count` header with the total number of matching assets (before pagination). The response body SHALL always be a flat JSON array of asset objects. When sorting, NULL values SHALL appear first regardless of sort direction.

#### Scenario: List all assets (no pagination)
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65` without a `limit` parameter
- **THEN** the system SHALL return all non-expired assets for that datastack as a flat JSON array

#### Scenario: Paginated listing
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65&limit=25&offset=50`
- **THEN** the system SHALL return at most 25 assets starting from offset 50, and include an `X-Total-Count` header with the total matching count

#### Scenario: Substring name filter
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65&name_contains=syn`
- **THEN** the system SHALL return only assets whose name contains "syn" (case-insensitive)

#### Scenario: Sort by mat_version with NULLs first
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65&sort_by=mat_version&sort_order=asc`
- **THEN** the system SHALL return assets sorted by mat_version ascending, with NULL mat_version assets appearing first

#### Scenario: Combined filters and pagination
- **WHEN** a user requests `GET /api/v1/assets/?datastack=minnie65&name_contains=syn&format=delta&limit=10&offset=0`
- **THEN** the system SHALL return at most 10 assets matching both filters, with `X-Total-Count` reflecting the total matching count

### Requirement: Asset update endpoint
The system SHALL accept partial asset updates via `PATCH /api/v1/assets/{id}` with a JSON body containing any subset of mutable fields: `maturity` (enum: "stable", "draft", "deprecated"), `access_group` (string or null), and `expires_at` (ISO datetime or null). Only fields present in the request body SHALL be updated; omitted fields SHALL remain unchanged. The caller SHALL have edit permission on the asset's datastack. The endpoint SHALL return the full updated asset response.

#### Scenario: Update maturity
- **WHEN** an authorized user sends `PATCH /api/v1/assets/{id}` with body `{"maturity": "deprecated"}`
- **THEN** the system SHALL update only the maturity field and return the full asset with maturity="deprecated"

#### Scenario: Update access_group to null
- **WHEN** an authorized user sends `PATCH /api/v1/assets/{id}` with body `{"access_group": null}`
- **THEN** the system SHALL set access_group to NULL and return the updated asset

#### Scenario: Update multiple mutable fields
- **WHEN** an authorized user sends `PATCH /api/v1/assets/{id}` with body `{"maturity": "draft", "expires_at": "2026-12-31T00:00:00Z"}`
- **THEN** the system SHALL update both fields and return the full updated asset

#### Scenario: Attempt to update immutable field
- **WHEN** a user sends `PATCH /api/v1/assets/{id}` with body containing `{"name": "new_name"}`
- **THEN** the system SHALL ignore the immutable field (or return 422) and not modify the name

#### Scenario: Unauthorized update
- **WHEN** a user without edit permission sends `PATCH /api/v1/assets/{id}`
- **THEN** the system SHALL return 403 Forbidden
