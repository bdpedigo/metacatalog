## Why

The catalog currently stores all asset metadata in a single untyped `properties` JSON blob. There is no enforcement of what metadata is declared for different asset types, and no system-derived metadata extracted from files. For tables specifically, critical information — column descriptions, cross-table references, row counts, schema — must be discoverable through the catalog to make it useful as a governance layer rather than just a bucket of paths.

## What Changes

- Lock down `asset_type` to a controlled enum (`table` initially, extensible to `image_volume`, `mesh`, etc.)
- Lock down `format` to a per-asset-type enum (`parquet`, `delta`, `lance` for tables)
- Add a `cached_metadata` JSON column for system-derived metadata (row counts, size, file-level info), populated by metadata extractors at registration time and refreshable on demand
- Add an `asset_columns` table for table-type assets, storing both derived column info (name, type, nullable) and user-declared annotations (description, references to other tables/columns, semantic type, unit)
- Add a metadata extraction pipeline that runs per `(asset_type, format)` at registration time, replacing the existing format sniff with a richer extractor
- Add a `POST /api/v1/assets/{id}/refresh-metadata` endpoint to re-derive cached metadata for mutable assets
- Update registration endpoints to accept and validate type-specific declared metadata (e.g., column annotations for tables)
- Update the CAVEclient to support the new registration fields and expose column metadata

## Capabilities

### New Capabilities
- `asset-type-validation`: Enforces `asset_type` and `format` as controlled vocabularies, validates that only known `(asset_type, format)` combinations are accepted, and dispatches type-specific validation rules at registration
- `table-column-metadata`: Stores per-column metadata for table-type assets, combining system-derived schema info (name, type, nullable) with user-declared annotations (description, references, semantic type, unit)
- `metadata-extraction`: Extracts and caches format-specific metadata (row counts, column schemas, partition info, etc.) from the underlying file at registration or on-demand refresh

### Modified Capabilities
- `asset-registry`: Registration must accept type-specific metadata fields, enforce `asset_type`/`format` enums, populate `cached_metadata` and `asset_columns` at registration time, and support metadata refresh
- `caveclient-catalog`: Client registration methods must support column annotations, and new methods needed to query column-level metadata

## Impact

- **Database**: New `asset_columns` table, new `cached_metadata`/`metadata_cached_at` columns on `assets`, migration to convert `asset_type`/`format` free strings to enums
- **API**: Registration request schema changes (new fields for column declarations), new refresh endpoint, column metadata query support on list/get
- **Validation pipeline**: Format sniff evolves into metadata extraction; new per-format extractors for parquet, delta, lance
- **CAVEclient**: `register_asset()` gains column annotation parameters, new methods for column metadata
- **Dependencies**: May need `pyarrow` (parquet metadata), `deltalake` (delta log reading), `lancedb` (lance metadata) as optional server-side dependencies for extractors
