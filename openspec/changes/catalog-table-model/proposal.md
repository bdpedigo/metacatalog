## Why

The catalog service uses a generic Asset model for all registered data objects, but tables (Delta Lake, Parquet) are the dominant use case and need first-class structure — discoverable column schemas, cached format-specific metadata, and semantic links back to materialization service tables. Currently, all type-specific metadata is stuffed into an untyped `properties` JSON bag, which means there's no schema enforcement, no auto-discovery of file metadata, and no way to express that "column X in my feature table is a foreign key into materialization table Y." A structured Table model with metadata extraction, column annotations, and column links solves these problems while keeping Asset generic for future non-table asset types.

## What Changes

- **Introduce single table inheritance**: table-specific columns (`format`, `mat_version`, `source`, `cached_metadata`, `metadata_cached_at`, `column_annotations`) are added as nullable columns on the existing `assets` table. The `asset_type` column serves as a polymorphic discriminator so SQLAlchemy returns `Table` instances for table rows and `Asset` instances for everything else. **BREAKING** — `format`, `mat_version` become table-specific rather than base Asset fields.
- **Add metadata extraction**: the service reads column schemas, row counts, partition info, and format-specific metadata directly from the data (Delta log, Parquet footer) and caches it as a JSONB blob on the asset row. Format-specific metadata (e.g., `delta_version`, `partition_columns`) is part of this blob, keyed by format — no separate DeltaLakeTable/ParquetTable DB models.
- **Add column annotations**: a separate JSONB field on `tables` stores user-provided column descriptions and column links. Column links are semantic references to materialization service tables (target table name + column, not catalog foreign keys). Annotations persist across metadata refreshes.
- **Read-time column merging**: the API merges cached column metadata with user annotations by column name, presenting a unified column view to consumers.
- **New table-specific write endpoints**: `POST /tables/preview` (discovery, no side effects), `POST /tables/register` (create + extract, optional annotations), `PATCH /tables/{id}/annotations` (replace semantics), `POST /tables/{id}/refresh` (re-extract cached metadata).
- **New table-specific read endpoint**: `GET /tables/` with table-specific filters (`format`, `mat_version`).
- **Unified read surface preserved**: `GET /assets/`, `GET /assets/{id}`, `DELETE /assets/{id}`, `POST /assets/{id}/access` continue to work across all asset types.
- **Column link validation at write time**: when a user submits column links, the service validates referenced materialization tables/columns exist. Links are stored as-is after validation (no ongoing referential integrity enforcement).

## Capabilities

### New Capabilities
- `table-model`: Single table inheritance data model with `asset_type` as polymorphic discriminator, table-specific nullable columns on `assets`, format-discriminated cached metadata JSONB, and column annotations JSONB with column link structure.
- `metadata-extraction`: Auto-discovery of column schemas, row counts, and format-specific metadata from Delta Lake and Parquet files. Preview, registration-time extraction, and manual refresh endpoint.
- `table-column-annotations`: User-provided column descriptions and semantic column links to materialization tables. Replace-semantics update endpoint. Read-time merging with cached column metadata.
- `table-endpoints`: Table-specific registration (with preview), annotation update, metadata refresh, and list endpoints.

### Modified Capabilities
- `asset-registry`: Base Asset model treats `format` and `mat_version` as table-specific (nullable on the shared table). `asset_type` becomes a discriminator column for single table inheritance. Registration endpoint remains for non-table assets.
- `caveclient-catalog`: Client gains `register_table`, `preview_table`, `list_tables`, `refresh_metadata`, and annotation update methods.

## Impact

- **Database**: The database is not yet live, so no data migration is required. The `assets` table schema is defined from scratch with table-specific nullable columns (`format`, `mat_version`, `source`, `cached_metadata`, `metadata_cached_at`, `column_annotations`) and `asset_type` as polymorphic discriminator. No separate `tables` table.
- **API**: New router for `/api/v1/tables/` endpoints. Existing `/api/v1/assets/` read endpoints return table-specific fields when `asset_type="table"`. `AssetRequest`/`AssetResponse` schemas change — `format` and `mat_version` become table-specific. **BREAKING** for callers passing these fields.
- **Metadata extraction**: New extraction pipeline that reads Delta logs and Parquet footers from cloud storage. Requires storage access (same credentials used for validation today).
- **CAVEclient**: New methods for table registration, preview, annotation, refresh. Existing `register_asset` still works for non-table assets.
- **MaterializationEngine**: Must update to use table registration endpoint instead of generic asset registration.
- **UI**: New registration form with auto-discovery and annotation editing form (future, not part of this change's backend work).
