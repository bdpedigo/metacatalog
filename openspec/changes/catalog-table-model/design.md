## Context

The catalog service currently stores all assets in a single `assets` table with an untyped `properties` JSON column for type-specific metadata. Tables (Delta Lake, Parquet) are the primary asset type but have no structural support — column schemas, row counts, and format-specific metadata are either absent or buried in `properties`. The service cannot auto-discover metadata from the files themselves, and there is no way to express semantic relationships between columns in a user's table and columns in materialization service tables.

Scale is modest: hundreds to low thousands of assets per datastack. Schema changes to underlying data are infrequent. The service does not own the bytes — users manage their own data in cloud storage.

## Goals / Non-Goals

**Goals:**
- First-class Table data model with structured metadata, separate from the generic Asset base
- Auto-discovery of column schemas and format-specific metadata from Delta Lake and Parquet files
- User-provided column annotations (descriptions, semantic links to mat tables) that persist independently of cached metadata refreshes
- Table-specific API endpoints for registration (with preview), annotation updates, metadata refresh, and listing
- Clean separation of cached (refreshable) vs. user-provided (persistent) metadata

**Non-Goals:**
- Automatic/periodic metadata refresh (manual only; easy to add later)
- Heuristic column link suggestion (e.g., matching `*_root_id` columns automatically)
- Sub-models per format in the DB (e.g., no separate `delta_tables` or `parquet_tables` DB tables)
- Relational normalization of column annotations or column links (JSONB is sufficient at this scale)
- UI implementation (API and data model only; UI is a separate effort)
- Catalog-internal foreign keys for column link targets (links reference mat service tables by name, not by catalog asset ID)

## Decisions

### 1. Single table inheritance for Asset → Table

**Decision**: Use SQLAlchemy single table inheritance. All asset types share the `assets` DB table. `format` and `mat_version` are base Asset fields (nullable) shared across all asset types — other asset types (e.g., image volumes with `precomputed`/`zarr` formats) will also use `format`, with valid values varying per `asset_type` and enforced at the application layer. Table-specific columns (`source`, `cached_metadata`, `metadata_cached_at`, `column_annotations`) are nullable columns on `assets`, populated only for table assets. The `asset_type` column serves as the polymorphic discriminator. SQLAlchemy's `Table(Asset)` subclass uses `polymorphic_identity="table"` with no separate `__tablename__`.

**Alternatives considered**:
- *`format` and `mat_version` as table-specific*: Originally considered making these table-only fields. But `format` is a generic concept (tables use `delta`/`parquet`, image volumes use `precomputed`/`zarr`) and `mat_version` may apply to other materialization-derived asset types. Keeping them on the base avoids moving fields between base and subclass as new asset types emerge.
- *Joined table inheritance*: A separate `tables` DB table joined 1:1 to `assets` via FK. Keeps the base table clean and allows NOT NULL constraints on table-specific columns. But adds JOINs on every polymorphic query, two-table inserts, and more complex uniqueness constraints across tables — overhead that isn't justified at our scale (hundreds to low thousands of assets) with only one subtype today.
- *Single table with JSONB for everything*: No DB-level columns for table-specific fields, everything in a single `details` JSONB blob. Even simpler, but loses the ability to index and filter on `format`, `mat_version`, `source` as real columns.

**Rationale**: At this scale with one subtype (tables), single table inheritance is the right tradeoff: real indexed columns for filterable fields, polymorphic dispatch in Python, no JOIN overhead, and trivial schema evolution. The cost is a few nullable columns that are meaningless for non-table assets — cosmetically messy but functionally harmless. If many asset types with many type-specific columns emerge later, migration to joined inheritance is straightforward.

### 2. Format-specific metadata as discriminated JSONB, not DB subtypes

**Decision**: The `cached_metadata` JSONB column on `assets` (populated only for table assets) holds format-specific metadata. Its shape varies by `format` (e.g., Delta tables include `delta_version`, `partition_columns`; Parquet includes `row_group_count`, `compression`). There are no `delta_tables` or `parquet_tables` DB tables.

**Alternatives considered**:
- *Joined inheritance for each format*: `DeltaLakeTable(Table)`, `ParquetTable(Table)` with their own DB tables. Gives real columns for format-specific fields, but all format-specific data is cached/auto-discovered — no user-provided format-specific fields exist yet. Adding a new format requires a migration.
- *Separate `cached_metadata` table per format*: Same overhead, no benefit.

**Rationale**: Format subtypes are entirely cached metadata. Validation happens at the application layer via Pydantic models keyed by format. Adding a new format requires only a new extractor and Pydantic model, no migration.

### 3. Separate JSONB fields for cached metadata vs. column annotations

**Decision**: Two JSONB columns on `assets`: `cached_metadata` (refreshable, replaced wholesale on extract) and `column_annotations` (persistent, user-provided). They are never mixed. These columns are nullable and only populated for table assets.

**Rationale**: This is the core design principle. Metadata refresh is a single atomic column swap — `UPDATE assets SET cached_metadata = $1, metadata_cached_at = $2 WHERE id = $3`. User annotations are never at risk of being clobbered. Read-time merging by column name produces a unified view for the API consumer.

### 4. Column links as JSONB inside column annotations, not a relational table

**Decision**: Column links (semantic references like "this column is a FK into `synapses.pre_pt_root_id`") are stored inside the `column_annotations` JSONB, nested under each column's annotation entry.

**Alternatives considered**:
- *Separate `column_links` relational table*: Enables `SELECT * FROM column_links WHERE target_table = 'synapses'` as a clean SQL query. But refresh becomes a multi-table delete+insert, and the query is achievable with JSONB operators + GIN index at this scale.
- *Separate `column_annotations` + `column_links` tables*: Maximum normalization, but 4+ tables and multi-table joins for a single asset read. Overkill for hundreds of assets.

**Rationale**: At hundreds-to-low-thousands scale, JSONB with a GIN index handles "find assets referencing table X" efficiently. Column links are validated at write time against the mat service and then stored as-is — no ongoing referential integrity needed.

### 5. Replace semantics for annotation updates

**Decision**: `PATCH /tables/{id}/annotations` uses replace semantics — the request body is the complete set of annotations, replacing whatever was stored.

**Alternatives considered**:
- *Merge semantics*: Only update mentioned columns, leave others untouched. Friendlier for partial updates but requires sentinel values for deletion and more complex merge logic.

**Rationale**: The annotation blob is small (one entry per column, ~50 max). Concurrent annotation editors are unlikely. The client/UI will always have the full state loaded when editing. Replace is simple, idempotent, and easy to reason about.

### 6. Separate write endpoints per asset type, unified read surface, with type-specific listing

**Decision**: Table registration, preview, annotation, and refresh have their own router (`/api/v1/tables/`). Read endpoints (`GET /assets/`, `GET /assets/{id}`, `DELETE /assets/{id}`, `POST /assets/{id}/access`) remain unified across all asset types. Additionally, `GET /api/v1/tables/` provides a table-specific listing endpoint that supports table-specific filters (`format`, `mat_version`, `source`) and guarantees table fields are present in every response. The unified `GET /assets/?asset_type=table` also works for basic table listing but cannot expose table-specific filters as cleanly.

**Rationale**: Write paths are genuinely different per type (different validation, different metadata extraction, different request bodies). A single `POST /assets/register` with a discriminator field would be a big dispatch switch. Read paths are naturally unified — "list all assets in a datastack" should include tables and non-tables with type-appropriate fields. The dedicated `list_tables` endpoint earns its keep by offering typed filters and a response model where table-specific fields are guaranteed present rather than optional. On the client side, `list_tables()` is the natural convenience method even if it's a thin wrapper over `list_assets(asset_type="table")`.

### 7. Always extract metadata at registration (no preview caching)

**Decision**: Metadata extraction runs fresh at both preview and registration time. Preview results are not cached server-side for reuse at registration.

**Rationale**: Extraction for Delta/Parquet is reading the log/footer from cloud storage — a few seconds, not minutes. Running it twice (preview then register) is simpler than caching preview results and associating them with a subsequent registration request. It also guarantees the registered metadata is fresh, not stale from a preview 10 minutes earlier.

## Risks / Trade-offs

- **[Nullable columns on base table]** → `format` and `mat_version` remain as nullable base Asset fields (shared across all asset types). Table-specific columns (`source`, `cached_metadata`, `metadata_cached_at`, `column_annotations`) are also nullable on the shared `assets` table. Non-table assets will have NULLs in table-specific columns. Accepted: at this scale with one subtype, the cosmetic cost is trivial and NOT NULL enforcement happens at the application layer via Pydantic validation.
- **[JSONB query performance]** → Column link queries (`find assets referencing table X`) use JSONB operators, not relational JOINs. Mitigated by GIN index on `column_annotations` and modest data scale. Can add a materialized view later if needed.
- **[Column name as join key]** → Cached columns and user annotations are merged by column name at read time. If a column is renamed in the data and metadata is refreshed, user annotations become orphaned (still stored, just not matched to a column). Accepted as a known limitation — annotations are inert when orphaned, and the column name change is visible to the user.
- **[Double extraction on preview+register]** → Extraction runs twice if the user previews first. Accepted at current scale; extraction is seconds, not minutes.
