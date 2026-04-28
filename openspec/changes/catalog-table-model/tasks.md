## 1. Data Model Changes

- [x] 1.1 Update `Asset` model: add `asset_type` as polymorphic discriminator column, keep `format` and `mat_version` as base nullable fields, add table-specific nullable columns (`source`, `cached_metadata`, `metadata_cached_at`, `column_annotations`) to the `assets` table
- [x] 1.2 Add `Table` SQLAlchemy model as single table inheritance subclass of `Asset` (`polymorphic_identity="table"`, no separate `__tablename__`)
- [x] 1.3 Add Pydantic models for cached metadata: `TableMetadata` (base), `DeltaMetadata`, `ParquetMetadata`
- [x] 1.4 Add Pydantic models for column annotations: `ColumnAnnotation`, `ColumnLink`
- [x] 1.5 Add Pydantic request/response models: `TableRequest`, `TableResponse` (with merged column view), `TablePreviewRequest`, `TablePreviewResponse`, `AnnotationUpdateRequest`
- [x] Stop! Prompt the user for feedback before continuing

## 2. Metadata Extraction Pipeline

- [ ] 2.1 Define `MetadataExtractor` base interface with `async extract(uri, credentials) -> TableMetadata`
- [ ] 2.2 Implement `DeltaMetadataExtractor` that reads Delta transaction log and returns `DeltaMetadata`
- [ ] 2.3 Implement `ParquetMetadataExtractor` that reads Parquet footer and returns `ParquetMetadata`
- [ ] 2.4 Add extractor registry keyed by format string (e.g., `{"delta": DeltaMetadataExtractor, "parquet": ParquetMetadataExtractor}`)
- [ ] Stop! Prompt the user for feedback before continuing


## 3. Column Link Validation

- [ ] 3.1 Implement column link validator that checks `target_table` and `target_column` exist in the materialization service for the target datastack
- [ ] 3.2 Integrate link validation into table registration and annotation update flows
- [ ] Stop! Prompt the user for feedback before continuing

## 4. Table Endpoints

- [ ] 4.1 Create `tables` router at `/api/v1/tables/`
- [ ] 4.2 Implement `POST /api/v1/tables/preview` — auth check, metadata extraction, return discovered metadata
- [ ] 4.3 Implement `POST /api/v1/tables/register` — auth check, duplicate check, metadata extraction, optional annotation validation, create asset row with table fields, return full record with merged columns
- [ ] 4.4 Implement `PATCH /api/v1/tables/{id}/annotations` — auth check, link validation, replace `column_annotations`, return updated record
- [ ] 4.5 Implement `POST /api/v1/tables/{id}/refresh` — auth check, re-extract metadata, replace `cached_metadata`, return updated record
- [ ] 4.6 Implement `GET /api/v1/tables/` — list with table-specific filters (`format`, `mat_version`, `source`)
- [ ] 4.7 Implement read-time column merging helper (merge `cached_metadata.columns` with `column_annotations` by column name)
- [ ] Stop! Prompt the user for feedback before continuing

## 5. Update Existing Asset Endpoints

- [ ] 5.1 Update `GET /api/v1/assets/` to return table-specific fields when `asset_type=table`
- [ ] 5.2 Update `GET /api/v1/assets/{id}` to return merged column view for table assets
- [ ] 5.3 Verify `AssetRequest`/`AssetResponse` schemas — `format` and `mat_version` remain as optional base fields, table-specific fields (`source`, `cached_metadata`, etc.) only on `TableResponse`
- [ ] 5.4 Update `POST /api/v1/assets/register` for non-table assets (ensure it still works without table-specific fields)
- [ ] Stop! Prompt the user for feedback before continuing

## 6. CAVEclient Updates

- [ ] 6.1 Add `register_table()` method to `CatalogClient`
- [ ] 6.2 Add `preview_table()` method to `CatalogClient`
- [ ] 6.3 Add `list_tables()` method to `CatalogClient`
- [ ] 6.4 Add `update_annotations()` method to `CatalogClient`
- [ ] 6.5 Add `refresh_metadata()` method to `CatalogClient`
- [ ] 6.6 Verify `register_asset()` — `format` and `mat_version` remain as optional base parameters
- [ ] Stop! Prompt the user for feedback before continuing

## 7. Tests

- [ ] 7.1 Test single table inheritance: creating table assets, querying via base and table models
- [ ] 7.2 Test metadata extraction: Delta and Parquet extractors with mock/fixture data
- [ ] 7.3 Test table registration endpoint: success, duplicate, validation failure
- [ ] 7.4 Test preview endpoint: returns metadata, no side effects
- [ ] 7.5 Test annotation update: replace semantics, link validation, auth check
- [ ] 7.6 Test metadata refresh: replaces cached_metadata, preserves column_annotations
- [ ] 7.7 Test read-time column merging: annotated columns, unannotated columns, orphaned annotations
- [ ] 7.8 Test list tables endpoint with filters
- [ ] 7.9 Test base asset endpoints still work for non-table assets after schema changes
