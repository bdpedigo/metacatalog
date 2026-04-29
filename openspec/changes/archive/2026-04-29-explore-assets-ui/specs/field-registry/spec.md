## ADDED Requirements

### Requirement: Field definition dataclass
The system SHALL define a `FieldDef` dataclass with the following attributes: `key` (string, dot-path into response model), `label` (string, display name), `default` (bool, shown by default in list), `formatter` (string: "text", "number", "datetime", "bytes", or "badge"), `filterable` (bool, appears in filter controls), `filter_type` (string: "substring", "exact", "enum", or "range"), `enum_values` (list of strings for enum filters), and `asset_types` (optional list of strings, None means all types).

#### Scenario: FieldDef with all attributes
- **WHEN** a FieldDef is created with `key="format", label="Format", default=True, formatter="badge", filterable=True, filter_type="enum", enum_values=["delta", "parquet", "precomputed"]`
- **THEN** the field definition SHALL be valid and usable by rendering and filter systems

### Requirement: Asset field registry
The system SHALL maintain an `ASSET_FIELDS` list of `FieldDef` entries covering all displayable asset and table fields. The registry SHALL include at minimum: name, mat_version, format, maturity, cached_metadata.n_rows (table only), source (table only), asset_type, mutability, created_at, owner, cached_metadata.n_columns (table only), cached_metadata.n_bytes (table only), and revision.

#### Scenario: Registry contains default fields
- **WHEN** the ASSET_FIELDS registry is queried for fields with `default=True`
- **THEN** it SHALL return at least: name, mat_version, format, maturity, and cached_metadata.n_rows

#### Scenario: Registry fields scoped to asset type
- **WHEN** rendering a non-table asset
- **THEN** fields with `asset_types=["table"]` (e.g., cached_metadata.n_rows, source) SHALL be excluded from display

### Requirement: Dot-path field resolution
The system SHALL provide a `resolve_field(asset_dict, key)` function that resolves dot-path keys against a nested dictionary. For example, `resolve_field(asset, "cached_metadata.n_rows")` SHALL traverse the nested structure and return the value at that path, or None if any segment is missing.

#### Scenario: Resolve nested field
- **WHEN** `resolve_field({"cached_metadata": {"n_rows": 1000}}, "cached_metadata.n_rows")` is called
- **THEN** it SHALL return 1000

#### Scenario: Resolve missing nested field
- **WHEN** `resolve_field({"cached_metadata": None}, "cached_metadata.n_rows")` is called
- **THEN** it SHALL return None

### Requirement: Format field Jinja2 filter
The system SHALL register a `format_field` Jinja2 filter that accepts an asset dictionary and a FieldDef, resolves the field value, and applies the formatter. Formatters SHALL produce: commas for "number" (e.g., "337,412,891"), human-readable sizes for "bytes" (e.g., "42.3 GB"), ISO or relative timestamps for "datetime", badge-style spans for "badge", and plain text for "text". None/missing values SHALL render as "—".

#### Scenario: Number formatter
- **WHEN** `format_field` is applied to a field with formatter="number" and value=337412891
- **THEN** it SHALL produce "337,412,891"

#### Scenario: Bytes formatter
- **WHEN** `format_field` is applied to a field with formatter="bytes" and value=45400000000
- **THEN** it SHALL produce a human-readable string like "42.3 GB"

#### Scenario: None value
- **WHEN** `format_field` is applied to a field with a None value
- **THEN** it SHALL produce "—"

### Requirement: Filter widget generation
The system SHALL provide a helper that generates HTML filter widget markup for a given FieldDef based on its `filter_type`: a text input with debounced HTMX trigger for "substring", a `<select>` with enum options for "enum", a number input for "exact", and paired min/max inputs for "range".

#### Scenario: Enum filter generates select element
- **WHEN** generating a filter widget for FieldDef with `filter_type="enum", enum_values=["delta", "parquet", "precomputed"]`
- **THEN** the output SHALL be a `<select>` element with an "All" option plus one `<option>` per enum value

#### Scenario: Substring filter generates text input
- **WHEN** generating a filter widget for FieldDef with `filter_type="substring"`
- **THEN** the output SHALL be a text `<input>` with HTMX attributes for debounced triggering (delay:300ms)

### Requirement: Startup validation
The system SHALL validate at application startup that all `FieldDef.key` values in the registry correspond to valid paths in the `AssetResponse` or `TableResponse` Pydantic models. If a registry key does not resolve to a known model field, the system SHALL raise a configuration error.

#### Scenario: Valid registry passes startup
- **WHEN** all registry keys match fields in AssetResponse or TableResponse
- **THEN** the application SHALL start normally

#### Scenario: Invalid registry key fails startup
- **WHEN** a registry entry has `key="nonexistent_field"`
- **THEN** the application SHALL fail to start with a clear error message indicating the invalid key
