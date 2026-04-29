## ADDED Requirements

### Requirement: Paginated asset list page
The UI SHALL render a paginated list of assets at `/ui/explore`. The list SHALL display assets for the currently selected datastack. Each page SHALL show up to 25 assets by default. The page SHALL display navigation controls (previous/next) and indicate the current page position (e.g., "Showing 1–25 of 142").

#### Scenario: User views explore page with assets
- **WHEN** a user navigates to `/ui/explore` with a datastack selected
- **THEN** the system SHALL display the first 25 assets sorted by name ascending, with pagination controls

#### Scenario: User navigates to next page
- **WHEN** a user clicks "Next" on the pagination controls
- **THEN** the system SHALL load the next page of assets via HTMX fragment swap without a full page reload

#### Scenario: Empty datastack
- **WHEN** a user navigates to `/ui/explore` for a datastack with no registered assets
- **THEN** the system SHALL display an empty state message (e.g., "No assets registered in this datastack")

### Requirement: Configurable column visibility
The UI SHALL render all available columns in the asset table with `data-col` attributes. The UI SHALL provide column toggle checkboxes above the table. Toggling a checkbox SHALL instantly show or hide the corresponding column via client-side CSS (no server round-trip). Column visibility preferences SHALL persist in `localStorage` across page loads.

#### Scenario: User hides a column
- **WHEN** a user unchecks the "Mat Version" column toggle
- **THEN** the "Mat Version" column header and all its cells SHALL be hidden immediately without a network request

#### Scenario: Column preferences persist
- **WHEN** a user has hidden "Mat Version" and "Source" columns
- **AND** navigates away and returns to `/ui/explore`
- **THEN** those columns SHALL remain hidden based on localStorage state

#### Scenario: Default column visibility
- **WHEN** a user visits `/ui/explore` for the first time (no localStorage state)
- **THEN** the system SHALL show default columns: name, mat_version, format, maturity, and n_rows (for tables)

### Requirement: Generic filtering from field registry
The UI SHALL render filter controls for each filterable field defined in the field registry. Filter widgets SHALL be auto-generated based on the field's `filter_type`: text input for substring filters, dropdown for enum filters, number input for exact numeric filters. The default filter bar SHALL show filters for default fields. An "Add filter" control SHALL allow adding filters for non-default filterable fields.

#### Scenario: Substring filter on name
- **WHEN** a user types "syn" into the name filter text input
- **AND** 300ms passes without further typing
- **THEN** the system SHALL fire an HTMX request with `name_contains=syn` and swap the table body with matching results

#### Scenario: Enum filter on format
- **WHEN** a user selects "delta" from the format dropdown filter
- **THEN** the system SHALL fire an HTMX request with `format=delta` and swap the table body with matching results

#### Scenario: Multiple active filters
- **WHEN** a user has name filter "syn" and format filter "delta" both active
- **THEN** the system SHALL apply both filters conjunctively (AND) and display only matching assets

#### Scenario: Reset filters
- **WHEN** a user clicks "Reset filters"
- **THEN** all filters SHALL be cleared and the full unfiltered asset list SHALL reload

### Requirement: Sortable columns
The UI SHALL allow sorting by clicking column headers. Clicking a column header SHALL toggle between ascending and descending sort order. The current sort column and direction SHALL be visually indicated (e.g., arrow icon). NULL values in sorted columns SHALL appear first.

#### Scenario: Sort by mat_version descending
- **WHEN** a user clicks the "Mat Version" column header twice (first click = ascending, second = descending)
- **THEN** the system SHALL display assets sorted by mat_version descending, with NULL mat_version entries appearing first

#### Scenario: Sort indicator
- **WHEN** a user sorts by "Name" ascending
- **THEN** the "Name" column header SHALL display a visual ascending sort indicator

### Requirement: Row click navigates to detail
The UI SHALL make each asset row clickable. Clicking a row SHALL navigate the user to the asset detail page at `/ui/explore/{id}`.

#### Scenario: User clicks an asset row
- **WHEN** a user clicks the row for asset "synapse_table"
- **THEN** the browser SHALL navigate to `/ui/explore/{asset_id}` showing the detail page for that asset

### Requirement: HTMX fragment endpoint for asset list
The UI SHALL expose `GET /ui/fragments/assets` that returns an HTML fragment containing the table body rows, pagination controls, and result count. This endpoint SHALL accept the same filter, sort, and pagination query params. HTMX requests from filters, pagination, and sort controls SHALL target this fragment endpoint.

#### Scenario: Fragment endpoint returns partial HTML
- **WHEN** an HTMX request is made to `GET /ui/fragments/assets?name_contains=syn&limit=25&offset=0`
- **THEN** the server SHALL return an HTML fragment (not a full page) containing table rows and pagination controls
