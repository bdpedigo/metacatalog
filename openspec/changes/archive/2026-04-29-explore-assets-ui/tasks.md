## 1. Field Registry

- [x] 1.1 Create `field_registry.py` with `FieldDef` dataclass and `ASSET_FIELDS` list
- [x] 1.2 Implement `resolve_field(asset_dict, key)` dot-path resolution helper
- [x] 1.3 Implement `format_field` Jinja2 filter (number, bytes, datetime, badge, text formatters)
- [x] 1.4 Add startup validation asserting registry keys against Pydantic response models
- [x] 1.5 Register `format_field` filter with the Jinja2 environment in app setup
- [x] 1.6 Write tests for `resolve_field` (nested paths, missing keys, None intermediates)
- [x] 1.7 Write tests for `format_field` (each formatter type, None handling, edge cases)
- [x] 1.8 Write test for startup validation (valid registry passes, invalid key raises)

## 2. API Pagination and Filtering

- [x] 2.1 Add `limit`, `offset`, `name_contains`, `sort_by`, `sort_order` params to `GET /api/v1/assets/`
- [x] 2.2 Implement ILIKE substring filter for `name_contains`
- [x] 2.3 Implement sorting with NULLs-first behavior
- [x] 2.4 Add `X-Total-Count` response header when `limit` is provided
- [x] 2.5 Write tests for pagination (limit/offset, no-limit returns all, X-Total-Count header)
- [x] 2.6 Write tests for substring filter and sorting (ILIKE matching, NULLs-first order)
- [x] 2.7 Add `AssetUpdateRequest` schema (maturity, access_group, expires_at — all optional)
- [x] 2.8 Implement `PATCH /api/v1/assets/{id}` endpoint with mutable-field-only updates
- [x] 2.9 Write tests for PATCH endpoint (update mutable fields, reject immutable fields, 403 unauthorized)

## 3. Explore Assets List Page

- [x] 3.1 Create `explore.html` template with generic table rendering loop driven by field registry
- [x] 3.2 Implement filter bar rendering from field registry (enum dropdowns, substring text inputs)
- [x] 3.3 Implement column toggle checkboxes with client-side JS (data-col, localStorage)
- [x] 3.4 Implement pagination controls (prev/next, page indicator)
- [x] 3.5 Add sortable column headers with HTMX sort triggers and sort direction indicators
- [x] 3.6 Create `GET /ui/fragments/assets` HTMX fragment endpoint (table rows + pagination)
- [x] 3.7 Update `GET /ui/explore` route to render full page with initial asset data
- [x] 3.8 Write tests for `/ui/explore` page render (authenticated, has table rows, pagination)
- [x] 3.9 Write tests for `/ui/fragments/assets` (filter params passed through, fragment response)

## 4. Asset Detail Page

- [x] 4.1 Create `explore_detail.html` template with summary card section
- [x] 4.2 Add cached metadata section (n_rows, n_columns, n_bytes, partition_columns) — table-only
- [x] 4.3 Add merged columns table section with links display — table-only
- [x] 4.4 Add `GET /ui/explore/{id}` route returning detail page
- [x] 4.5 Handle non-table assets (show summary + properties, hide table-specific sections)
- [x] 4.6 Write tests for detail page (table asset shows metadata + columns, non-table hides them, 404 for invalid ID)

## 5. Asset Edit Page

- [x] 5.1 Create `explore_edit.html` template with mutable field controls (maturity radio, access_group text, expires_at date)
- [x] 5.2 Integrate column annotation editor (reuse builder component from register page)
- [x] 5.3 Add `GET /ui/explore/{id}/edit` route rendering the edit form with pre-populated values
- [x] 5.4 Add `POST /ui/explore/{id}/edit` route handling form submission (calls PATCH API internally)
- [x] 5.5 Implement error handling (re-render form with error message, preserve input)
- [x] 5.6 Add edit permission check (403 for unauthorized users)
- [x] 5.7 Write tests for edit page (renders form, saves changes, 403 for unauthorized, error re-render)

## 6. Styling and Polish

- [x] 6.1 Add CSS for data table (striped rows, hover, clickable row cursor)
- [x] 6.2 Add CSS for filter bar layout and widgets
- [x] 6.3 Add CSS for column toggle checkboxes area
- [x] 6.4 Add CSS for detail page cards and columns table
- [x] 6.5 Add CSS for badge formatter (maturity/format/source badges)
- [x] 6.6 Add empty state styling for no-results and no-metadata scenarios
