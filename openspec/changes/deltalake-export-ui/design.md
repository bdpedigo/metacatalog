## Context

The MaterializationEngine already has:
- A **Delta Lake export backend** (`deltalake_export.py`) with Celery tasks, auto-discovery of output specs from table indexes, auto-sizing of partition counts, and Redis-backed progress tracking.
- A **table upload wizard UI** (Flask + Jinja2 + Alpine.js) with a 4-step wizard pattern, localStorage state persistence, Redis progress polling, and a "Running Uploads" monitoring dashboard.
- **Existing REST endpoints** for listing datastacks, versions, and tables that the upload wizard already consumes.

The export pipeline is triggered via `POST .../write_deltalake/...` with optional `output_specs` in the body. Progress is polled via `GET` on the same URL. There is no frontend for any of this.

## Goals / Non-Goals

**Goals:**
- Provide a web UI for admins to configure and launch Delta Lake exports without API knowledge
- Auto-discover output specs and present them for review/editing before launch
- Allow per-spec override of `target_file_size_mb` (inheriting from a global default)
- Show real-time progress with phase transitions, row counts, and log messages
- Display Python exception messages on failure
- Reuse existing UI framework (Alpine.js, wizardStore pattern, polling)
- Design for future multi-export concurrency without implementing it now

**Non-Goals:**
- Multi-export dashboard (show all running exports) — single-export view for now, architecture supports expansion
- Exposing `flush_threshold_bytes` or `optimize_max_concurrent_tasks` in UI — these are implementation details
- Custom spec creation from scratch in the UI (only editing auto-discovered specs + adding more)
- WebSocket/SSE for real-time updates — polling is sufficient and matches existing patterns

## Decisions

### 1. 3-step wizard (not 4)

The upload wizard has 4 steps because its flow is sequential with distinct data at each stage (file → schema → metadata → process). For export, global config (target partition size, output bucket) is known upfront and belongs with table selection. Specs are the only complex review step.

**Steps**: Select + Config → Review Specs → Confirm & Launch

**Alternative considered**: 4 steps with separate "Global Options" step. Rejected because the only user-facing global option is `target_partition_size_mb`, which doesn't warrant its own page.

### 2. Spec discovery as a separate endpoint

`POST /materialize/deltalake/discover-specs` runs `discover_default_output_specs()` + `estimate_bytes_per_row()` + `resolve_n_partitions()` and returns the result without enqueuing an export.

**Rationale**: Decouples discovery from execution. Enables the wizard to show specs before committing. Opens future path for dispatching individual specs to separate workers.

**Alternative considered**: Running discovery as part of the export task and making the user wait. Rejected because it eliminates the ability to review/edit before launch.

### 3. Discovery results cached in Redis (short TTL)

Key: `deltalake_specs:{datastack}:v{version}:{table}`, TTL: 10 minutes.

**Rationale**: Discovery hits the frozen DB (inspect indexes, pg_class stats, possibly TABLESAMPLE). Caching prevents redundant work on page refresh or step navigation. Short TTL avoids stale data.

**Alternative considered**: localStorage only. Rejected because discovery is expensive and should survive browser refresh without re-running.

### 4. Per-spec `target_file_size_mb` with global inheritance

`DeltaLakeOutputSpec` gains `target_file_size_mb: int | None = None`. When `None`, the global value from Step 1 (defaulting to env `DELTALAKE_TARGET_PARTITION_SIZE_MB`) is used. The recalculate endpoint resolves `n_partitions` per-spec using the effective value.

**Rationale**: Different partitioning strategies may benefit from different file sizes (e.g., smaller spatial partitions for faster range queries). Global default covers 90% of cases; per-spec override covers the rest.

### 5. Extended progress payload (same endpoint)

The existing `GET .../write_deltalake/...` returns additional fields:
```json
{
  "status": "exporting",
  "phase": "streaming",
  "rows_processed": 176341000,
  "total_rows": 337312429,
  "percent_complete": 52.3,
  "error": null,
  "log_entries": ["12:01 Resolved 2 output specs", ...],
  "last_updated": "2026-05-05T12:15:33Z"
}
```

`log_entries` sourced from a capped Redis list (`RPUSH` + `LTRIM` to 100 entries). `error` is `str(e)` from caught exceptions.

**Alternative considered**: Separate `/logs` endpoint. Rejected for simplicity — one poll gets everything.

### 6. Recalculate endpoint (pure computation)

`POST /materialize/deltalake/recalculate` takes `{ row_count, bytes_per_row, specs }` and returns specs with recomputed `n_partitions`. No DB access — just `resolve_n_partitions()` math.

**Rationale**: Lets the UI recalculate partition counts after the user edits `target_file_size_mb` or `n_partitions` overrides without hitting the frozen DB again.

### 7. State key scheme for future concurrency

Redis keys use `(datastack, version, table)` tuple. For future concurrent exports of the same table, a job_id suffix can be appended:
```
deltalake_export:{datastack}:v{version}:{table}          # current
deltalake_export:{datastack}:v{version}:{table}:{job_id} # future
```

No code changes needed now — just documenting the extension point.

## Risks / Trade-offs

- **[Stale discovery cache]** → 10-minute TTL mitigates. If table structure changes between discovery and launch (unlikely for frozen DBs), the export task re-validates internally.
- **[Large log_entries list]** → Capped at 100 entries via `LTRIM`. Polling returns full list each time (acceptable at 100 items).
- **[No auth on discover-specs beyond dataset_admin]** → Same permission model as existing export endpoint. Acceptable since discovery is read-only against frozen DB.
- **[Single export per (datastack, version, table) key]** → Acceptable for concurrency-1. Future work adds job_id suffix.
- **[Error messages may leak internal details]** → `str(e)` from Python exceptions shown to admins only (dataset_admin required). Acceptable for admin tooling.
