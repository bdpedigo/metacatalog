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

### 1. Joined table inheritance for Asset → Table

**Decision**: Use SQLAlchemy joined table inheritance. A `tables` DB table joins 1:1 to `assets` via `asset_id` FK. Table-specific columns (`format`, `mat_version`, `source`) are real columns on `tables`, not nullable columns on `assets`.

**Alternatives considered**:
- *Single table with nullable columns*: Simpler, but non-table assets carry dead weight (`format`, `mat_version` are meaningless for them). Table-specific columns can't have NOT NULL constraints.
- *Single table with JSONB for everything*: No DB-level enforcement of table-specific fields. Can't index `mat_version` or `format` as real columns.

**Rationale**: The joined approach keeps the base `assets` table clean for future asset types (meshes, image stacks) while giving tables real queryable columns. SQLAlchemy's `__mapper_args__` with `polymorphic_on` handles the join transparently.

### 2. Format-specific metadata as discriminated JSONB, not DB subtypes

**Decision**: The `cached_metadata` JSONB column on `tables` holds format-specific metadata. Its shape varies by `format` (e.g., Delta tables include `delta_version`, `partition_columns`; Parquet includes `row_group_count`, `compression`). There are no `delta_tables` or `parquet_tables` DB tables.

**Alternatives considered**:
- *Joined inheritance for each format*: `DeltaLakeTable(Table)`, `ParquetTable(Table)` with their own DB tables. Gives real columns for format-specific fields, but all format-specific data is cached/auto-discovered — no user-provided format-specific fields exist yet. Adding a new format requires a migration.
- *Separate `cached_metadata` table per format*: Same overhead, no benefit.

**Rationale**: Format subtypes are entirely cached metadata. Validation happens at the application layer via Pydantic models keyed by format. Adding a new format requires only a new extractor and Pydantic model, no migration.

### 3. Separate JSONB fields for cached metadata vs. column annotations

**Decision**: Two JSONB columns on `tables`: `cached_metadata` (refreshable, replaced wholesale on extract) and `column_annotations` (persistent, user-provided). They are never mixed.

**Rationale**: This is the core design principle. Metadata refresh is a single atomic column swap — `UPDATE tables SET cached_metadata = $1, metadata_cached_at = $2`. User annotations are never at risk of being clobbered. Read-time merging by column name produces a unified view for the API consumer.

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

- **[BREAKING API change]** → `format` and `mat_version` removed from base Asset schema. Mitigated by coordinating with CAVEclient and MaterializationEngine updates. Version the API if needed.
- **[Data migration complexity]** → Existing `assets` rows with `asset_type="table"` must be migrated into `tables` rows with `format` and `mat_version` extracted from the old columns. Mitigated by writing a one-time Alembic migration with explicit data transformation.
- **[JSONB query performance]** → Column link queries (`find assets referencing table X`) use JSONB operators, not relational JOINs. Mitigated by GIN index on `column_annotations` and modest data scale. Can add a materialized view later if needed.
- **[Column name as join key]** → Cached columns and user annotations are merged by column name at read time. If a column is renamed in the data and metadata is refreshed, user annotations become orphaned (still stored, just not matched to a column). Accepted as a known limitation — annotations are inert when orphaned, and the column name change is visible to the user.
- **[Double extraction on preview+register]** → Extraction runs twice if the user previews first. Accepted at current scale; extraction is seconds, not minutes.
