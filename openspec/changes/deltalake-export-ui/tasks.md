## 1. Backend — Extend DeltaLakeOutputSpec and Progress Model

- [ ] 1.1 Add `target_file_size_mb: int | None = None` field to `DeltaLakeOutputSpec` dataclass
- [ ] 1.2 Update `write_deltalake_table` to thread per-spec `target_file_size_mb` through `resolve_n_partitions`
- [ ] 1.3 Add `phase` and `error` fields to `set_deltalake_export_status()` and the Redis progress payload
- [ ] 1.4 Create `append_deltalake_log(datastack, version, table_name, message)` helper using `RPUSH` + `LTRIM(100)`
- [ ] 1.5 Add phase-transition log calls in `write_deltalake_table` (discovering, computing_boundaries, streaming, optimizing, complete, failed)
- [ ] 1.6 Capture `str(e)` on exception and pass to `set_deltalake_export_status(..., error=str(e))`
- [ ] 1.7 Update `get_deltalake_export_progress()` to read and include log entries from the Redis list

## 2. Backend — Discovery and Recalculate Endpoints

- [ ] 2.1 Create Flask blueprint for deltalake UI at `/materialize/deltalake/`
- [ ] 2.2 Implement `POST /materialize/deltalake/discover-specs` endpoint (auth, frozen DB introspection, caching result in Redis with 10min TTL)
- [ ] 2.3 Implement `POST /materialize/deltalake/recalculate` endpoint (pure computation, no DB access)
- [ ] 2.4 Add endpoint to serve environment defaults (`target_partition_size_mb`, `output_bucket`) for Step 1 pre-population

## 3. Frontend — Wizard Framework

- [ ] 3.1 Create wizard page template (`templates/deltalake_wizard.html`) extending `base.html` with step indicator (reuse upload wizard CSS pattern)
- [ ] 3.2 Create `static/js/deltalakeWizardStore.js` for Alpine.js state management with localStorage persistence
- [ ] 3.3 Create step templates: `templates/deltalake/step1.html`, `step2.html`, `step3.html`
- [ ] 3.4 Wire up wizard navigation routes in the deltalake blueprint

## 4. Frontend — Step 1 (Select + Config)

- [ ] 4.1 Implement datastack dropdown (server-rendered, filtered by dataset_admin permission)
- [ ] 4.2 Implement version dropdown (fetch from existing versions endpoint on datastack change, default to latest)
- [ ] 4.3 Implement table dropdown (fetch from existing tables endpoint on version change)
- [ ] 4.4 Implement target_partition_size_mb input with server default pre-populated
- [ ] 4.5 Implement "Discover Specs" button with loading spinner and error display
- [ ] 4.6 Create `static/js/deltalakeStep1.js` with Alpine.js component logic

## 5. Frontend — Step 2 (Review Specs)

- [ ] 5.1 Implement spec card rendering from discovery results (partition_by, strategy, n_partitions, zorder, bloom, geometry)
- [ ] 5.2 Implement editable fields: n_partitions override, target_file_size_mb override
- [ ] 5.3 Implement "Remove spec" button with minimum-1 guard
- [ ] 5.4 Implement "Recalculate" button that POSTs to recalculate endpoint and updates displayed values
- [ ] 5.5 Display table metadata (row_count, bytes_per_row) as read-only context
- [ ] 5.6 Create `static/js/deltalakeStep2.js` with Alpine.js component logic

## 6. Frontend — Step 3 (Confirm & Launch)

- [ ] 6.1 Implement summary display (datastack, version, table, specs table with final n_partitions and target URIs)
- [ ] 6.2 Implement "Launch Export" button that POSTs to existing export endpoint with configured specs
- [ ] 6.3 Handle error responses (Delta Lake already exists, etc.) with inline error display
- [ ] 6.4 On success, clear localStorage state and redirect to monitoring page
- [ ] 6.5 Create `static/js/deltalakeStep3.js` with Alpine.js component logic

## 7. Frontend — Monitoring Page

- [ ] 7.1 Create `templates/deltalake/running_exports.html` with card-in-grid layout (supports future N cards)
- [ ] 7.2 Implement progress bar, rows counter, phase label, and status badge
- [ ] 7.3 Implement log panel with auto-scroll (pause on manual scroll, resume when scrolled to bottom)
- [ ] 7.4 Implement error display panel (red border, shown only on `status: "failed"`)
- [ ] 7.5 Implement polling (5s interval, stop on terminal status)
- [ ] 7.6 Add "New Export" link navigating to wizard Step 1
- [ ] 7.7 Create `static/js/deltalakeRunningExports.js` with polling and DOM update logic

## 8. Integration and Testing

- [ ] 8.1 Register deltalake blueprint in the Flask app factory
- [ ] 8.2 Add navigation link to deltalake export UI from the main MaterializationEngine admin page
- [ ] 8.3 Write unit tests for `discover-specs` endpoint (mock frozen DB introspection)
- [ ] 8.4 Write unit tests for `recalculate` endpoint (pure computation)
- [ ] 8.5 Write unit tests for extended progress payload (phase, error, log_entries)
- [ ] 8.6 Manual end-to-end test: wizard flow through to monitoring with a real frozen DB
