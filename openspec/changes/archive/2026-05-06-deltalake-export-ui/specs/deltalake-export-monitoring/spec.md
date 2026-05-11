## ADDED Requirements

### Requirement: Monitoring page displays export progress
The system SHALL provide a monitoring page at `/materialize/deltalake/running-exports` that displays the current export's progress including: status, phase, progress bar (percent complete), rows processed / total rows, and last updated timestamp. The page SHALL poll the existing GET progress endpoint every 5 seconds while the export is active.

#### Scenario: Active export displays progress
- **WHEN** the user navigates to the monitoring page with an active export
- **THEN** the system SHALL display a progress card with a progress bar at the current percent, rows processed count, total rows count, current phase, and status

#### Scenario: Polling updates progress in real-time
- **WHEN** an export is in progress
- **THEN** the system SHALL poll the status endpoint every 5 seconds and update the progress bar, row counts, and phase without page reload

#### Scenario: Polling stops on terminal status
- **WHEN** the export reaches status `complete` or `failed`
- **THEN** the system SHALL stop polling and display the final state

### Requirement: Monitoring page displays log entries
The system SHALL display a scrollable log panel showing log entries from the export. New entries SHALL appear at the bottom. The panel SHALL auto-scroll to the latest entry unless the user has manually scrolled up.

#### Scenario: Log entries appear during export
- **WHEN** the progress endpoint returns `log_entries` with new messages
- **THEN** the system SHALL append new entries to the log panel

#### Scenario: Auto-scroll behavior
- **WHEN** the user has not manually scrolled the log panel
- **THEN** the system SHALL auto-scroll to show the latest log entry

#### Scenario: Manual scroll pauses auto-scroll
- **WHEN** the user scrolls up in the log panel
- **THEN** the system SHALL stop auto-scrolling until the user scrolls back to the bottom

### Requirement: Monitoring page displays errors
The system SHALL display error messages when an export fails. The error message SHALL be the Python exception string from the backend. The error SHALL be displayed in a visually distinct error panel (red border/background).

#### Scenario: Export failure shows error
- **WHEN** the progress endpoint returns status `failed` with a non-null `error` field
- **THEN** the system SHALL display the error message in a red-bordered error panel

#### Scenario: No error on success
- **WHEN** the export completes successfully
- **THEN** the system SHALL display a success indicator with no error panel

### Requirement: Monitoring page displays phase transitions
The system SHALL display the current phase of the export prominently. Phases include: `discovering_specs`, `computing_boundaries`, `streaming`, `optimizing`, `complete`, `failed`.

#### Scenario: Phase updates during export
- **WHEN** the export transitions from `streaming` to `optimizing`
- **THEN** the system SHALL update the displayed phase label

### Requirement: Monitoring page supports future multi-export listing
The system SHALL render export status as a card within a container that can hold multiple cards. The data model and DOM structure SHALL support rendering N export cards in a grid layout, even though initially only one export is shown.

#### Scenario: Single export renders as card in grid
- **WHEN** one export is active
- **THEN** the system SHALL render it as a single card within a grid container (not a full-page layout)

### Requirement: Navigation from monitoring to wizard
The system SHALL provide a link/button to start a new export from the monitoring page, navigating back to the wizard Step 1.

#### Scenario: Start new export link
- **WHEN** the user is on the monitoring page
- **THEN** the system SHALL display a "New Export" link that navigates to the wizard
