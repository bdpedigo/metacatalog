## Context

The catalog service is a FastAPI JSON API with no UI. Dataset admins interact via Swagger docs, raw HTTP, or CAVEclient. The service currently has: an auth system (middle_auth delegation with Bearer tokens and cookie support, OAuth redirect helpers), a validation pipeline with individually callable checks (`check_uri_reachable`, `check_format_sniff`, `check_name_reservation`), and materialization engine integration via hand-rolled httpx calls. The catalog-table-model change (in progress) adds table-specific endpoints (`POST /tables/preview`, `POST /tables/register`, `PATCH /tables/{id}/annotations`) and Pydantic models for table metadata, column annotations, and column links. This frontend change builds on that foundation.

## Goals / Non-Goals

**Goals:**
- Server-rendered UI embedded in the existing FastAPI app — no separate service, no JS build pipeline
- Interactive table registration with metadata preview, incremental validation, and column link builder
- Materialization service reference data (tables, views, column schemas) available to the UI via cached server-side queries
- Google OAuth login flow using existing middle_auth infrastructure
- Page layout that accommodates future additions (asset browsing, relationship graph) without restructuring

**Non-Goals:**
- Asset browsing / exploration UI (placeholder nav item only; separate future change)
- Relationship graph visualization
- Custom CSS framework or design system — use a minimal classless/utility CSS library
- Mobile responsiveness (admin desktop tool)
- Offline support or PWA features
- New materialization engine endpoints (work with existing endpoints, propose new ones separately)
- Client-side routing or SPA architecture

## Decisions

### 1. HTMX + Jinja2 for server-rendered dynamic UI

**Decision**: Use Jinja2 templates for all HTML rendering and HTMX for dynamic server interactions (preview, name check, cascading dropdowns). Alpine.js or vanilla JS for purely client-side interactions (add/remove link rows, show/hide form sections).

**Alternatives considered**:
- *Full page reloads (plain Jinja2)*: No JS at all. But the registration form has multiple mid-page server interactions (preview, name check, column link dropdowns) — full reloads would lose form state and feel clunky.
- *React / Vue SPA*: Rich interactivity but introduces a JS build pipeline (Node.js, npm, webpack/vite), a separate deployment artifact, CORS configuration, and requires all data to flow through JSON API endpoints. Overkill for an admin forms tool.
- *Streamlit / Gradio*: Fast to prototype but awkward deployment story, limited styling control, doesn't embed cleanly in an existing FastAPI app.

**Rationale**: The team is Python-first. HTMX keeps all rendering logic in Python templates — the server returns HTML fragments for dynamic updates, not JSON for the browser to render. No build pipeline, no npm. The 90% of interactions (preview → populate columns, name check → show status, table dropdown → populate column dropdown) are "send data to server, swap part of the page" — HTMX's core pattern. The 10% that's purely client-side (add/remove a link row) is trivial with Alpine.js or vanilla JS. Future features like a relationship graph can use an isolated JS library (D3, Cytoscape) as an "island" within an otherwise server-rendered page.

### 2. Same-app architecture — UI routes share the service layer

**Decision**: UI route handlers live in the catalog FastAPI app alongside the JSON API routes. They call the same Python service functions (metadata extraction, validation checks, DB queries) directly — no internal HTTP calls.

**Alternatives considered**:
- *UI calls JSON API via fetch*: The browser fetches JSON from `/api/v1/...` and JS builds DOM. Adds a redundant HTTP hop when the UI handler could call the function directly. Also requires all UI data to have a JSON API surface.
- *Separate frontend service*: A distinct microservice for the UI that calls the catalog API. Two things to deploy and coordinate. No benefit for a small admin tool.

**Rationale**: The UI's dynamic interactions (preview, name check, mat table queries) need server-side logic. Since the UI is in the same process, route handlers call service functions directly. The JSON API continues to exist for CAVEclient and programmatic access. The two surfaces share the service layer but have independent route handlers.

### 3. CAVEclient for materialization engine queries with service token

**Decision**: The catalog adds CAVEclient as a Python dependency and uses it to query the materialization engine for table lists, view lists, and column schemas. These queries authenticate with a service token (configured via `SERVICE_TOKEN` env var), not the user's token. CAVEclient calls are synchronous; they run via `asyncio.to_thread` to avoid blocking the event loop.

**Alternatives considered**:
- *Hand-rolled httpx calls (current pattern)*: The validation code already calls mat engine endpoints via httpx. Extending this for table lists, view lists, and schema resolution means duplicating URL construction and response parsing that CAVEclient already handles.
- *Catalog queries mat DB directly*: Tight coupling, credential sharing, bad service boundary.

**Rationale**: CAVEclient wraps the materialization API including the emannotationschemas schema-type-to-columns resolution, which is non-trivial. Using a service token (rather than forwarding the user's token) for reference data queries is correct because mat table metadata is not user-specific — it's shared reference data. This also simplifies caching (one cache per datastack, not per user). The `to_thread` pattern is already established in the codebase for `cloudpathlib` and `polars` calls.

### 4. TTL caching for materialization reference data

**Decision**: Cache mat table lists, view lists, and column schemas with a short TTL (e.g., 5 minutes). Cache is keyed by `(datastack, mat_version)` for table/view lists and `(datastack, mat_version, table_name)` for column schemas. Cache is in-process (simple dict or `cachetools.TTLCache`), not shared across workers.

**Alternatives considered**:
- *No caching*: Every dropdown open hits the mat engine. Mat engine calls take ~100-300ms. During column link configuration, a user might open the table dropdown multiple times — noticeable latency.
- *Redis or external cache*: Shared across workers but adds an infrastructure dependency for a modest performance gain.

**Rationale**: The data changes infrequently (tables/views don't appear or disappear during a registration session). In-process TTL cache is simple, no new dependencies, and handles the single-worker case well. For multi-worker deployments, each worker warms its own cache — acceptable given the small data size and short TTL.

### 5. Column link targets include both tables and views

**Decision**: The column link "target table" dropdown shows both materialization tables and views as linkable targets. The catalog fetches both (`get_tables()` + `get_views()`) and merges them into a single list, distinguishing by type. For column schema resolution: views use the existing `get_view_schema()` endpoint (returns columns directly); tables use `get_table_metadata()` → schema type → `schema_definition()` → `get_col_info()` to resolve columns.

**Alternatives considered**:
- *Tables only*: Simpler but artificially limits what users can link to. Views are a valid link target.
- *New unified mat engine endpoint*: A `GET .../linkable-targets` that returns both tables and views with column schemas in one call. Cleaner but requires a mat engine change and deployment.

**Rationale**: Support both from the start. The two-path resolution (views are direct, tables go through emannotationschemas) is a code complexity cost but avoids blocking on a mat engine change. If/when a unified endpoint is added, the catalog can switch to it transparently.

### 6. Incremental validation during form fill

**Decision**: Validation happens progressively as the user fills the form, not only at registration time:
- **Preview click**: URI reachability + format detection + schema extraction. Diagnostic errors displayed inline.
- **Name field blur**: Name availability check (reservation + duplicate). Inline ✓/✗ indicator.
- **Register click**: Full validation pipeline re-runs (including fresh metadata extraction). Errors shown on the form.

The existing validation functions (`check_uri_reachable`, `check_format_sniff`, `check_name_reservation`) are already individually callable. A new lightweight route handler for name checking (combining reservation check and DB duplicate check) is needed.

**Alternatives considered**:
- *Validate only at registration time*: Simpler, but the user doesn't discover problems (name taken, URI unreachable) until the end.

**Rationale**: Early feedback reduces wasted effort. The validation functions are already modular — exposing them incrementally is low cost.

### 7. Google OAuth login via middle_auth redirect

**Decision**: The UI uses the existing middle_auth OAuth flow. Unauthenticated users visiting `/ui/*` are redirected to middle_auth's authorize endpoint, which handles Google OAuth. On callback, the catalog sets a `middle_auth_token` cookie. All subsequent UI and dynamic requests include this cookie, which the existing auth middleware extracts and validates.

Routes:
- `GET /ui/login` — redirects to `get_authorize_url(redirect=<original_url>)`
- `GET /ui/callback` — receives token, sets cookie via `create_token_cookie_response`, redirects to original URL
- `GET /ui/logout` — clears cookie, redirects to login

**Rationale**: The building blocks already exist in the catalog's auth module (`get_authorize_url`, `create_token_cookie_response`, cookie extraction in `_extract_token`). This wires them into a redirect flow. No new auth infrastructure.

### 8. Service credentials for cloud storage access

**Decision**: Metadata extraction (preview and registration) uses the catalog service's own cloud storage credentials (service account / ambient credentials), not the user's credentials. The user must be authorized to register tables in the catalog, but the service independently accesses the data files.

**Rationale**: The service needs its own access to cloud storage for metadata extraction to work. User authorization (can this user register tables?) and service data access (can the catalog read this URI?) are separate concerns. This is consistent with how `cloudpathlib` already works in the codebase — it uses ambient credentials.

### 9. Page layout with datastack-scoped navigation

**Decision**: A shared base template provides persistent navigation:
- Top bar: service name, datastack selector dropdown, user info / logout
- Left sidebar: Register (primary), Explore Assets (placeholder)
- Content area: page-specific content

Datastack selection is global — changing it affects all views. The selected datastack is stored in a cookie or URL query parameter so it persists across page loads.

**Rationale**: Admins work within one datastack at a time. A global selector avoids repeating datastack selection on every form. The layout accommodates future pages (browse, detail, graph) as additional sidebar items without restructuring.

## Risks / Trade-offs

- **[Dependency on catalog-table-model]** → The registration UI depends on table-specific endpoints and models that are still being implemented. Mitigated by: sequencing this change after catalog-table-model's endpoint work, or building the UI against the Pydantic models (which already exist) and wiring to endpoints later.
- **[CAVEclient as sync dependency in async app]** → CAVEclient is synchronous. All calls go through `asyncio.to_thread`, which occupies a thread pool worker for the duration. At admin-level traffic this is negligible. If it becomes an issue, an async CAVEclient wrapper or direct httpx calls can replace it.
- **[Two-path column resolution for tables vs. views]** → Tables require schema type → emannotationschemas resolution; views have a direct schema endpoint. This is more code paths to maintain. Mitigated by TTL caching (both paths cache the final column list) and future unification via a mat engine endpoint.
- **[In-process cache not shared across workers]** → Each worker warms its own cache. Acceptable at current scale. If the catalog scales to many workers, an external cache (Redis) can replace `TTLCache` with minimal code change.
- **[HTMX learning curve]** → Team is unfamiliar with HTMX. Mitigated by: HTMX's small API surface (~15 attributes), abundant documentation, and the interactions in this change being textbook HTMX patterns (form submit → swap result, dropdown change → swap dependent dropdown).
- **[No offline / degraded mode]** → Every form interaction requires the server. If the catalog is down, the UI is down. Acceptable for an admin tool.
