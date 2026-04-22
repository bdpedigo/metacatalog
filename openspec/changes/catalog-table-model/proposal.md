## Why

The catalog service uses a generic Asset model for all registered data objects, but tables (Delta Lake, Parquet) are the dominant use case and need first-class structure — discoverable column schemas, cached format-specific metadata, and semantic links back to materialization service tables. Currently, all type-specific metadata is stuffed into an untyped `properties` JSON bag, which means there's no schema enforcement, no auto-discovery of file metadata, and no way to express that "column X in my feature table is a foreign key into materialization table Y." A structured Table model with metadata extraction, column annotations, and column links solves these problems while keeping Asset generic for future non-table asset types.

## What Changes

- **Introduce joined table inheritance**: a new `tables` DB table extends `assets` with table-specific columns (`format`, `mat_version`, `source`, `cached_metadata`, `column_annotations`). **BREAKING** — `format`, `mat_version` move off the base Asset model onto Table.
- **Add metadata extraction**: the service reads column schemas, row counts, partition info, and format-specific metadata directly from the data (Delta log, Parquet footer) and caches it as a JSONB blob on the `tables` row. Format-specific metadata (e.g., `delta_version`, `partition_columns`) is part of this blob, keyed by format — no separate DeltaLakeTable/ParquetTable DB models.
- **Add column annotations**: a separate JSONB field on `tables` stores user-provided column descriptions and column links. Column links are semantic references to materialization service tables (target table name + column, not catalog foreign keys). Annotations persist across metadata refreshes.
- **Read-time column merging**: the API merges cached column metadata with user annotations by column name, presenting a unified column view to consumers.
- **New table-specific write endpoints**: `POST /tables/preview` (discovery, no side effects), `POST /tables/register` (create + extract, optional annotations), `PATCH /tables/{id}/annotations` (replace semantics), `POST /tables/{id}/refresh` (re-extract cached metadata).
- **New table-specific read endpoint**: `GET /tables/` with table-specific filters (`format`, `mat_version`).
- **Unified read surface preserved**: `GET /assets/`, `GET /assets/{id}`, `DELETE /assets/{id}`, `POST /assets/{id}/access` continue to work across all asset types.
- **Column link validation at write time**: when a user submits column links, the service validates referenced materialization tables/columns exist. Links are stored as-is after validation (no ongoing referential integrity enforcement).

## Capabilities

### New Capabilities
- `table-model`: Joined table inheritance data model, Table-specific DB schema, format-discriminated cached metadata JSONB, and column annotations JSONB with column link structure.
- `metadata-extraction`: Auto-discovery of column schemas, row counts, and format-specific metadata from Delta Lake and Parquet files. Preview, registration-time extraction, and manual refresh endpoint.
- `table-column-annotations`: User-provided column descriptions and semantic column links to materialization tables. Replace-semantics update endpoint. Read-time merging with cached column metadata.
- `table-endpoints`: Table-specific registration (with preview), annotation update, metadata refresh, and list endpoints.

### Modified Capabilities
- `asset-registry`: Base Asset model loses `format` and `mat_version` (moved to Table). `asset_type` becomes a discriminator column for joined table inheritance. Registration endpoint remains for non-table assets.
- `caveclient-catalog`: Client gains `register_table`, `preview_table`, `list_tables`, `refresh_metadata`, and annotation update methods.

## Impact

- **Database**: Migration to add `tables` table with joined inheritance FK to `assets`. Existing asset rows with `asset_type="table"` need data migration to populate `tables` rows. `format` and `mat_version` columns removed from `assets`. **BREAKING** schema change.
- **API**: New router for `/api/v1/tables/` endpoints. Existing `/api/v1/assets/` read endpoints return table-specific fields when `asset_type="table"` (via joined query). `AssetRequest`/`AssetResponse` schemas change — `format` and `mat_version` removed from base. **BREAKING** for callers passing these fields.
- **Metadata extraction**: New extraction pipeline that reads Delta logs and Parquet footers from cloud storage. Requires storage access (same credentials used for validation today).
- **CAVEclient**: New methods for table registration, preview, annotation, refresh. Existing `register_asset` still works for non-table assets.
- **MaterializationEngine**: Must update to use table registration endpoint instead of generic asset registration.
- **UI**: New registration form with auto-discovery and annotation editing form (future, not part of this change's backend work).
