## Context

The catalog service has a working registration flow (UI + API) and a placeholder "Explore Assets" page. The base template, HTMX infrastructure, auth, datastack cookie, and CSS foundation are all in place. The `GET /api/v1/assets/` endpoint returns all non-expired assets for a datastack with exact-match filters. The UI needs a browsing experience that scales as asset counts grow and adapts as the data model evolves.

Key existing patterns:
- HTMX for dynamic interactions (fragments swapped into the DOM)
- Jinja2 templates extending `base.html`
- `_page_context()` helper for shared template variables
- `require_ui_auth` dependency for auth gating
- Cookie-based datastack scoping

## Goals / Non-Goals

**Goals:**
- Paginated, filterable asset browsing with HTMX-powered interactions
- Schema-evolution-friendly rendering driven by a field registry (add a field = add one registry entry)
- Instant column visibility toggling (no round-trip)
- Detail page showing full asset info including table-specific metadata and merged columns
- Edit page for mutable fields reusing existing annotation builder components
- Backward-compatible API changes (no breaking existing consumers)

**Non-Goals:**
- Full-text search across all fields (substring on name is sufficient)
- Bulk operations (multi-select, batch delete)
- Real-time updates / WebSocket push
- Per-user saved filter presets (localStorage column visibility is enough)
- View asset resolution (separate change: catalog-view-definitions)

## Decisions

### 1. Field registry drives all rendering

**Decision:** A Python `FieldDef` dataclass registry is the single source of truth for list columns, filter widgets, detail page layout, and column toggles.

**Rationale:** The user needs the UI to update with minimal modification as the backend schema evolves. A data-driven approach means adding a new field to the explore page requires one registry entry — no template changes.

**Alternatives considered:**
- Per-field template markup: simpler initially but requires template edits for every schema change
- Frontend component library (React/Vue): over-engineering for server-rendered HTMX app

**Structure:**
```python
@dataclass
class FieldDef:
    key: str              # dot-path into response (e.g. "cached_metadata.n_rows")
    label: str            # display name
    default: bool         # shown in list by default?
    formatter: str        # "text" | "number" | "datetime" | "bytes" | "badge"
    filterable: bool      # appears in filter bar?
    filter_type: str      # "substring" | "exact" | "enum" | "range"
    enum_values: list     # for enum filters
    asset_types: list     # None = all, ["table"] = table only
```

A `format_field(asset, field_def)` Jinja2 filter resolves dot-paths and applies formatters.

### 2. Pagination via optional `limit`/`offset` + header

**Decision:** `GET /api/v1/assets/` accepts optional `limit` and `offset`. When `limit` is provided, the response includes an `X-Total-Count` header. The response body is always a flat list.

**Rationale:** Keeps backward compatibility (no limit → all results, same shape). Avoids a paginated envelope that would break existing consumers. The header provides total count for UI pagination controls.

**Alternatives considered:**
- Paginated envelope `{items, total, limit, offset}`: cleaner but breaking change
- Cursor-based pagination: more complex, unnecessary for this scale
- Separate endpoint (`/assets/search`): fragmentation

### 3. Client-side column visibility toggle

**Decision:** Server renders all columns with `data-col` attributes. JavaScript toggles `display:none` via CSS class. Preferences stored in `localStorage`.

**Rationale:** Instant toggling (~0ms) vs. HTMX re-fetch (~50-150ms). Payload overhead is negligible for 25-row pages with ~12 columns.

**Alternatives considered:**
- Server-side `columns` param with HTMX re-fetch: snappy but not instant, adds round-trip
- Column visibility in URL params: shareable but over-complex for a personal preference

### 4. Generic filter application from registry

**Decision:** Filters are auto-generated from the field registry based on `filter_type`. The API endpoint iterates registered filterable fields and applies appropriate SQL predicates.

**Filter type mapping:**
| filter_type | UI Widget | SQL |
|-------------|-----------|-----|
| substring | text input (debounced) | `ILIKE '%value%'` |
| exact | number input | `= value` |
| enum | dropdown | `= value` |
| range | min/max inputs | `BETWEEN` |

**Rationale:** Adding a filterable field requires only a registry entry. The endpoint and template adapt automatically.

### 5. NULL `mat_version` sorts first

**Decision:** When sorting by `mat_version`, NULL values (user-uploaded tables without a mat version) appear first.

**Rationale:** User decision — NULLs first groups user uploads at the top when sorting ascending by version.

### 6. Mutable vs. immutable field contract

**Decision:** The following fields are mutable after creation via `PATCH /api/v1/assets/{id}`:
- `maturity` (stable ↔ draft ↔ deprecated)
- `access_group`
- `expires_at`

Column annotations are updated via the existing `PATCH /api/v1/tables/{id}/annotations`.

Cached metadata is refreshed via `POST /api/v1/tables/{id}/refresh` (system-managed, not user-editable directly).

All other fields (name, uri, format, datastack, mat_version, revision, asset_type, owner, is_managed, mutability, source, created_at) are immutable identity/provenance fields.

### 7. Three-page navigation pattern

**Decision:**
- `/ui/explore` — paginated list with filters
- `/ui/explore/{id}` — read-only detail page
- `/ui/explore/{id}/edit` — edit form for mutable fields

**Rationale:** Separate pages keep concerns clean. Detail page is lightweight (no form overhead). Edit page reuses annotation builder from register flow.

## Risks / Trade-offs

- **[JSON dot-path resolution in SQL]** Filtering on `cached_metadata.n_rows` requires SQLAlchemy JSON path operators. → Mitigation: wrap in a helper that handles JSONB extraction; only enable range filters on JSON fields that are indexed or small-cardinality.
- **[All columns in payload]** Client-side column toggle means server always ships all columns even if hidden. → Mitigation: At 25 rows × 12 columns this is <5KB extra; acceptable. Revisit if asset counts per page grow large.
- **[Registry drift]** Field registry could get out of sync with the Pydantic response model. → Mitigation: Add a startup assertion that validates registry keys against `AssetResponse` / `TableResponse` model fields.
- **[Filter injection]** Substring filter uses `ILIKE` which could be slow on large tables. → Mitigation: Use `name` column (already indexed); for JSON fields, only support exact/enum filters initially.
