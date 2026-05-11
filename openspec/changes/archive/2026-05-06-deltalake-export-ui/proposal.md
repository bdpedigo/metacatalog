## Why

The MaterializationEngine's Delta Lake export pipeline is fully functional but API-only — there is no user-facing interface to configure, launch, or monitor exports. Admins must manually construct API calls with output specs. Meanwhile, a mature upload wizard UI (Flask + Alpine.js) already exists with patterns for multi-step configuration, progress polling, and error display. Adding an export UI using the same framework lets admins self-serve table dumps without needing to understand the API contract or spec discovery internals.

## What Changes

- Add a 3-step wizard UI for configuring and launching Delta Lake exports (select table + global config → review/edit auto-discovered specs → confirm & launch)
- Add a monitoring page showing export progress, phase transitions, log tail, and error messages
- Add a `POST /materialize/deltalake/discover-specs` endpoint that runs spec discovery without enqueuing an export
- Add a `POST /materialize/deltalake/recalculate` endpoint for recomputing partition counts from modified specs
- Extend `DeltaLakeOutputSpec` with an optional per-spec `target_file_size_mb` override
- Extend the existing progress Redis payload with `phase`, `error`, and `log_entries` fields
- Add a `append_deltalake_log()` helper that writes phase-transition messages to a capped Redis list

## Capabilities

### New Capabilities
- `deltalake-export-wizard`: 3-step wizard UI for configuring and launching Delta Lake exports (table selection, spec review/editing, confirmation)
- `deltalake-export-monitoring`: Real-time monitoring page with progress bar, phase display, log tail, and error rendering
- `deltalake-spec-discovery-api`: Endpoint to run output spec auto-discovery and return results without triggering export

### Modified Capabilities
- `table-endpoints`: Extending the existing Delta Lake export endpoint with richer progress reporting (phase, error, log_entries) and per-spec target_file_size_mb

## Impact

- **MaterializationEngine**: New Flask blueprint for deltalake UI (templates, static JS, routes). Modifications to `deltalake_export.py` for richer progress/logging and per-spec file size. New Redis key for log entries list.
- **Existing endpoints**: The existing `GET .../write_deltalake/...` progress endpoint returns additional fields (backwards-compatible addition).
- **Dependencies**: No new dependencies — uses existing Flask, Alpine.js, Redis, Celery stack.
- **Auth**: Requires `dataset_admin` permission (same as existing export endpoint).
