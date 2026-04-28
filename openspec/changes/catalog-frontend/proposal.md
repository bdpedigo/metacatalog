## Why

The catalog service is a JSON API with no user-facing interface — dataset admins must use Swagger docs or raw HTTP calls to register tables, which is error-prone and provides no guidance during the multi-step registration flow. Table registration in particular involves metadata discovery, column annotation, and column link configuration, all of which benefit from an interactive form that pre-populates fields from auto-discovered metadata and provides cascading dropdowns for linking to materialization tables and views. A lightweight frontend embedded in the catalog service gives admins a guided registration experience and lays the groundwork for future asset browsing and relationship visualization.

## What Changes

- **Add a server-rendered UI** to the catalog FastAPI app using Jinja2 templates and HTMX for dynamic interactions. No separate frontend service or JS build pipeline. HTMX handles server round-trips (preview, name validation, column link dropdowns); Alpine.js or vanilla JS handles purely client-side interactions (add/remove link rows, show/hide sections).
- **Table registration page** (`/ui/register`): a multi-step form where the user enters a URI, triggers metadata preview (format detection, column schema extraction), fills in table name and column annotations (descriptions + links to materialization tables/views), and submits for registration. Incremental validation occurs throughout — name availability checked on blur, column link targets populated via cascading dropdowns, and diagnostic error messages displayed inline for preview/registration failures.
- **Materialization service proxy endpoints**: the UI needs to populate dropdowns for column link targets. The catalog will query the materialization engine (via CAVEclient, using a service token) for available tables, views, and their column schemas, with TTL caching. These server-side route handlers support the dynamic form interactions.
- **Name availability check endpoint**: exposes the existing `check_name_reservation` and duplicate-check logic as an independently callable validation, so the UI can check name availability on field blur without running the full validation pipeline.
- **Google OAuth login flow**: users authenticate via middle_auth's OAuth redirect, and a session cookie (`middle_auth_token`) persists identity across UI page loads. The building blocks exist (authorize URL builder, cookie helper); this change wires them into a login/callback/logout flow for the UI.
- **App-level layout with navigation**: a shared page layout with persistent nav (datastack selector, Register, Explore Assets) that supports adding future pages (browse, detail, relationship graph) without structural changes. The "Explore Assets" section is a placeholder in V1.
- **CAVEclient as a service dependency**: the catalog adds CAVEclient as a dependency for querying materialization tables, views, and schemas. Calls are run via `asyncio.to_thread` to avoid blocking the async event loop. A service token (not the user's token) authenticates these reference-data queries.

## Capabilities

### New Capabilities
- `catalog-ui`: Server-rendered UI framework for the catalog service — Jinja2 templates, HTMX, shared layout with datastack-scoped navigation, Google OAuth login flow, and static asset serving.
- `table-registration-ui`: Interactive table registration page with metadata preview, incremental validation (name check, URI reachability, format detection), column annotation editing, and column link builder with cascading materialization table/view + column dropdowns.
- `mat-service-proxy`: Server-side handlers that query the materialization engine (via CAVEclient with service token) for tables, views, and column schemas. Includes TTL caching of reference data.

### Modified Capabilities
- `asset-registry`: Name availability check (`check_name_reservation` + duplicate check) is exposed as an independently callable validation, not only as part of the full registration pipeline.

## Impact

- **Catalog service**: New dependencies — `jinja2`, `python-multipart` (form parsing), `caveclient`. New directories under `src/cave_catalog/`: `templates/`, `static/`, and a `routers/ui.py` (or similar) for UI route handlers. HTMX and Alpine.js loaded via CDN `<script>` tags, no npm/Node.js.
- **Configuration**: New settings — `SERVICE_TOKEN` (for mat engine queries), optional `CAVECLIENT_SERVER_ADDRESS`. Existing `AUTH_SERVICE_URL` and `AUTH_ENABLED` settings are reused for the OAuth flow.
- **Deployment**: No new services. The UI is served from the same FastAPI app. Static assets (CSS, any local JS) are served via FastAPI's `StaticFiles` mount.
- **Materialization Engine**: No changes required in V1. The catalog queries existing endpoints (`GET .../tables`, `GET .../views`, `GET .../views/{view}/schema`). For regular table column schemas, the catalog resolves the schema type name through emannotationschemas via CAVEclient. A future unified "linkable targets with columns" endpoint would simplify this but is not a blocker.
- **Dependencies on catalog-table-model**: The table registration UI depends on the table-specific endpoints (`POST /tables/preview`, `POST /tables/register`) and models (`TablePreviewRequest`, `TableResponse`, `ColumnAnnotation`, `ColumnLink`) being implemented. This change should be sequenced after or in parallel with catalog-table-model's endpoint work.
