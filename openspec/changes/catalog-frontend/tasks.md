## 1. UI Framework Setup

- [ ] 1.1 Add dependencies to `pyproject.toml`: `jinja2`, `python-multipart`; add `caveclient` dependency for mat service proxy
- [ ] 1.2 Create directory structure: `src/cave_catalog/templates/`, `src/cave_catalog/static/`, `src/cave_catalog/routers/ui.py`
- [ ] 1.3 Configure Jinja2Templates instance and mount StaticFiles in the FastAPI app (`app.py`)
- [ ] 1.4 Create base template (`templates/base.html`) with layout: top bar (service name, datastack selector, user info/logout), left sidebar (Register, Explore Assets placeholder), main content area. Include HTMX via CDN `<script>` tag.
- [ ] 1.5 Add basic CSS (either a classless CSS library or minimal custom CSS in `static/`)
- [ ] Stop! Prompt the user for feedback before continuing

## 2. Auth Flow

- [ ] 2.1 Add `/ui/login` route that redirects to `get_authorize_url(redirect=<original_url>)`
- [ ] 2.2 Add `/ui/callback` route that receives token from middle_auth, sets `middle_auth_token` cookie via `create_token_cookie_response`, and redirects to original destination
- [ ] 2.3 Add `/ui/logout` route that clears the cookie and redirects to login
- [ ] 2.4 Add auth guard dependency for UI routes: if no valid cookie, redirect to `/ui/login` (not 401 JSON)
- [ ] Stop! Prompt the user for feedback before continuing

## 3. Datastack Selector

- [ ] 3.1 Add route handler to populate available datastacks (query from config or mat engine)
- [ ] 3.2 Implement datastack selector in base template — persists selection in cookie, scopes all subsequent operations
- [ ] 3.3 Ensure all UI route handlers read the selected datastack from cookie and pass it to templates/service functions
- [ ] Stop! Prompt the user for feedback before continuing

## 4. Mat Service Proxy

- [ ] 4.1 Add `SERVICE_TOKEN` and `CAVECLIENT_SERVER_ADDRESS` settings to `config.py`
- [ ] 4.2 Create `mat_proxy.py` module with functions: `get_mat_tables(datastack, version)`, `get_mat_views(datastack, version)`, `get_linkable_targets(datastack, version)`, `get_target_columns(datastack, version, target_name, target_type)`. All use CAVEclient via `asyncio.to_thread` with service token.
- [ ] 4.3 Add TTL cache (e.g., `cachetools.TTLCache`) keyed by `(datastack, version)` for table/view lists and `(datastack, version, target_name)` for column schemas
- [ ] 4.4 Add UI route handlers that return HTML fragments (for HTMX) or JSON for the link builder: linkable targets list, column list for a selected target
- [ ] Stop! Prompt the user for feedback before continuing

## 5. Name Availability Check

- [ ] 5.1 Add `GET /api/v1/assets/check-name` endpoint — combines `check_name_reservation()` with DB duplicate check, returns `{available, reason, existing_id}`
- [ ] 5.2 Add UI route handler for name check that returns an HTML fragment (✓/✗ indicator with message) for HTMX swap on field blur
- [ ] Stop! Prompt the user for feedback before continuing

## 6. Registration Page — Preview Step

- [ ] 6.1 Create registration page template (`templates/register.html`) with: URI input field, Preview button, placeholder area for metadata and column table
- [ ] 6.2 Wire Preview button via HTMX: `POST` to a UI route handler that calls the table preview service function, returns an HTML fragment with discovered metadata (format, row count, format-specific info) and column table
- [ ] 6.3 Implement diagnostic error rendering: distinct error messages for URI unreachable, format unrecognizable, and format-specific parse failures — displayed inline in the preview area
- [ ] Stop! Prompt the user for feedback before continuing

## 7. Registration Page — Annotation Step

- [ ] 7.1 Render the column table with editable description fields and "Add Link" button per column row
- [ ] 7.2 Implement "Add Link" interaction: clicking adds a link form row with link type selector, target table/view dropdown (HTMX-loaded from mat proxy), and target column dropdown (HTMX-loaded, cascading from target selection)
- [ ] 7.3 Implement "Remove Link" interaction (client-side only, no server round-trip)
- [ ] 7.4 Add table name field with HTMX `hx-trigger="blur"` wired to the name check handler, displaying inline ✓/✗
- [ ] 7.5 Add mat_version field (optional integer input)
- [ ] Stop! Prompt the user for feedback before continuing

## 8. Registration Page — Submit Step

- [ ] 8.1 Wire Register button: collect all form data (URI, name, mat_version, column annotations with links), POST to a UI route handler that calls the table registration service function
- [ ] 8.2 On success: render a success template fragment with table ID, name, details, and "Register Another" link
- [ ] 8.3 On failure: re-render the form with validation errors displayed inline, user input preserved
- [ ] Stop! Prompt the user for feedback before continuing

## 9. Explore Assets Placeholder

- [ ] 9.1 Create placeholder page (`templates/explore.html`) at `/ui/explore` with a "Coming soon" message
- [ ] Stop! Prompt the user for feedback before continuing

## 10. Tests

- [ ] 10.1 Test auth flow: unauthenticated redirect, callback sets cookie, logout clears cookie
- [ ] 10.2 Test mat proxy functions: table list, view list, column schema resolution, caching behavior (TTL, cache hit/miss)
- [ ] 10.3 Test name availability endpoint: available, reserved, duplicate cases
- [ ] 10.4 Test registration page renders and HTMX interactions return HTML fragments (use FastAPI test client)
- [ ] 10.5 Test preview error cases: URI unreachable, format unrecognizable, parse failure — verify diagnostic error messages
- [ ] 10.6 Test registration submission: success response, validation error response with preserved input
