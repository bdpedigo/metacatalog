## Why

The catalog UI has a placeholder "Explore Assets" page. Users need a way to browse, filter, and inspect the assets registered in a datastack — discovering what tables exist, their schema, metadata, and annotations. This is the primary read-path for the catalog and complements the existing registration write-path.

## What Changes

- Replace the "Coming soon" placeholder at `/ui/explore` with a paginated, filterable asset list
- Add an asset detail page at `/ui/explore/{id}` showing full metadata, columns, and annotations
- Add an asset edit page at `/ui/explore/{id}/edit` for mutable fields (maturity, annotations, access_group, expires_at)
- Extend `GET /api/v1/assets/` with pagination (`limit`/`offset`), substring name search (`name_contains`), sorting (`sort_by`/`sort_order`), and a total count response header
- Add `PATCH /api/v1/assets/{id}` endpoint for updating mutable asset fields
- Introduce a field registry that drives list columns, filters, and detail rendering — enabling schema evolution without template changes

## Capabilities

### New Capabilities
- `explore-assets-page`: Paginated asset list with configurable columns, generic filtering (type-inferred from field registry), and client-side column visibility toggles
- `asset-detail-page`: Read-only detail view showing all asset fields, cached metadata, and merged column information for tables
- `asset-edit-page`: Edit form for mutable asset fields (maturity, column_annotations, access_group, expires_at) with the existing annotation builder reused
- `field-registry`: Data-driven field definition system that maps asset model fields to display labels, formatters, filter types, and column visibility defaults — single source of truth for UI rendering

### Modified Capabilities
- `asset-registry`: Add pagination support (optional `limit`/`offset` query params, `X-Total-Count` header), substring name filter (`name_contains`), sorting (`sort_by`/`sort_order`), and a `PATCH /api/v1/assets/{id}` endpoint for mutable field updates

## Impact

- **Backend**: `routers/assets.py` gains pagination/sort/search params and a new PATCH endpoint. New `field_registry.py` module.
- **Frontend**: New templates for explore list, detail, and edit pages. New HTMX fragment endpoints in `routers/ui.py`. JS for client-side column toggle (localStorage).
- **CSS**: Additional styles for data tables, filter bar, badges, detail cards.
- **Existing consumers**: `GET /api/v1/assets/` remains backward-compatible (no `limit` → returns all, flat list). New `X-Total-Count` header is additive.
