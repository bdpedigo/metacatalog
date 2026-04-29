## ADDED Requirements

### Requirement: Jinja2 template rendering
The catalog service SHALL serve HTML pages using Jinja2 templates. Templates SHALL be stored under `src/cave_catalog/templates/`. The FastAPI app SHALL mount a `Jinja2Templates` instance configured to load from this directory.

#### Scenario: HTML page rendered from template
- **WHEN** a user requests `GET /ui/register`
- **THEN** the server SHALL return an HTML page rendered from a Jinja2 template with `Content-Type: text/html`

### Requirement: Static asset serving
The catalog service SHALL serve static assets (CSS, images, local JS if any) via FastAPI's `StaticFiles` mount at `/static/`. Static files SHALL be stored under `src/cave_catalog/static/`.

#### Scenario: Static file served
- **WHEN** a browser requests `GET /static/style.css`
- **THEN** the server SHALL return the file with appropriate Content-Type and caching headers

### Requirement: HTMX for dynamic interactions
The UI SHALL use HTMX (loaded via CDN `<script>` tag) for all server-initiated dynamic interactions. Dynamic route handlers SHALL return HTML fragments (not full pages) for HTMX-triggered requests.

#### Scenario: HTMX fragment response
- **WHEN** an HTMX-triggered request is made (identified by the `HX-Request` header)
- **THEN** the server SHALL return an HTML fragment suitable for DOM insertion, not a full page

### Requirement: Shared page layout with navigation
The UI SHALL use a base template providing a persistent layout with: a top bar (service name, datastack selector, user info/logout), a left sidebar with navigation items (Register as primary, Explore Assets as placeholder), and a main content area. All UI pages SHALL extend this base template.

#### Scenario: Navigation is persistent across pages
- **WHEN** a user navigates between UI pages
- **THEN** the top bar, datastack selector, and sidebar navigation SHALL remain visible and consistent

#### Scenario: Explore Assets placeholder
- **WHEN** a user clicks the "Explore Assets" navigation item
- **THEN** the system SHALL display a placeholder page indicating this feature is coming soon

### Requirement: Datastack-scoped navigation
The UI SHALL provide a datastack selector in the top navigation bar. The selected datastack SHALL persist across page loads (via cookie or URL parameter) and SHALL scope all UI operations — mat table queries, name checks, registration, and listing.

#### Scenario: Datastack selection persists
- **WHEN** a user selects datastack "minnie65_phase3" from the selector
- **AND** navigates to a different UI page
- **THEN** the datastack selector SHALL still show "minnie65_phase3" as selected

#### Scenario: Datastack scopes operations
- **WHEN** the user has selected datastack "minnie65_phase3"
- **AND** triggers a table preview or name check
- **THEN** the operation SHALL be scoped to the "minnie65_phase3" datastack

### Requirement: Google OAuth login flow
The UI SHALL authenticate users via middle_auth's OAuth redirect flow. Unauthenticated users visiting any `/ui/*` route SHALL be redirected to the middle_auth authorize endpoint. On successful authentication, the catalog SHALL set a `middle_auth_token` session cookie and redirect the user to their original destination.

#### Scenario: Unauthenticated user is redirected to login
- **WHEN** an unauthenticated user (no valid `middle_auth_token` cookie) visits `/ui/register`
- **THEN** the system SHALL redirect them to the middle_auth authorize URL with a redirect parameter pointing back to `/ui/register`

#### Scenario: Successful login callback
- **WHEN** middle_auth redirects back to `/ui/callback` with a valid token
- **THEN** the system SHALL set the `middle_auth_token` cookie and redirect the user to their original destination

#### Scenario: Logout clears session
- **WHEN** a user visits `/ui/logout`
- **THEN** the system SHALL clear the `middle_auth_token` cookie and redirect to the login page
