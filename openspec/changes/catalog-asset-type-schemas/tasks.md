## 1. Data Model & Schema Changes

- [ ] 1.1 Add `AssetType` and `TableFormat` StrEnum classes to `schemas.py`
- [ ] 1.2 Update `AssetRequest` and `AssetResponse` to use `AssetType` enum for `asset_type` and accept `column_annotations` field
- [ ] 1.3 Add `cached_metadata` (JSONB, nullable) and `metadata_cached_at` (timestamptz, nullable) columns to the `Asset` SQLAlchemy model
- [ ] 1.4 Create `AssetColumn` SQLAlchemy model with all fields (asset_id, column_name, column_type, nullable, ordinal, description, semantic_type, unit, ref_table, ref_column, ref_datastack, ref_relationship)
- [ ] 1.5 Create Alembic migration for `cached_metadata`, `metadata_cached_at` columns and `asset_columns` table
- [ ] 1.6 Add Pydantic models for column annotations (`ColumnAnnotation`, `ColumnReference`) and column response (`ColumnResponse`)
- [ ] 1.7 Add type-specific properties schemas (`TableBaseProperties`, format extensions) and `(asset_type, format)` validation registry

## 2. Metadata Extraction Pipeline

- [ ] 2.1 Define `ExtractionResult` dataclass/model with `cached_metadata`, `column_schema`, and `validation` fields
- [ ] 2.2 Implement parquet metadata extractor (n_rows, n_columns, size_bytes, column schema from parquet footer via polars/pyarrow)
- [ ] 2.3 Implement delta metadata extractor (n_rows, n_columns, delta_version, partition_columns, column schema via deltalake)
- [ ] 2.4 Create `METADATA_EXTRACTORS` registry keyed by `(asset_type, format)` replacing `FORMAT_SNIFFERS`
- [ ] 2.5 Add lance metadata extractor stub (basic schema extraction, to be fleshed out when lance support is needed)

## 3. Validation Pipeline Updates

- [ ] 3.1 Add `type_validation` check to `ValidationReport` and validation pipeline (validates asset_type enum, format enum, and (asset_type, format) combination)
- [ ] 3.2 Add type-specific properties validation check (e.g., `description` required for tables)
- [ ] 3.3 Replace `check_format_sniff` with metadata extraction in `run_validation_pipeline`, rename report field from `format_sniff` to `metadata_extraction`
- [ ] 3.4 Add column annotation merge logic: match declared annotations to extracted columns, warn on mismatches
- [ ] 3.5 Add soft enforcement warnings for mat-sourced tables with unannotated `*_root_id` columns

## 4. Registration & Refresh Endpoints

- [ ] 4.1 Update `POST /register` to run metadata extraction, populate `cached_metadata`/`metadata_cached_at`, and create `asset_columns` rows
- [ ] 4.2 Update `POST /register` to accept and merge `column_annotations` from request body
- [ ] 4.3 Update `POST /validate` to include type validation, metadata extraction, and column annotation warnings in report
- [ ] 4.4 Implement `POST /api/v1/assets/{id}/refresh-metadata` endpoint (re-extract, update cached_metadata, update/add/flag asset_columns, preserve declared annotations)
- [ ] 4.5 Update `GET /api/v1/assets/{id}` and `GET /api/v1/assets/` to include `cached_metadata`, `metadata_cached_at`, and `columns` in responses

## 5. CAVEclient Updates

- [ ] 5.1 Update `register_asset()` to accept `column_annotations` parameter and include in request body
- [ ] 5.2 Update `validate_asset()` to accept `column_annotations` parameter
- [ ] 5.3 Add `refresh_metadata(asset_id)` method to `CatalogClient`
- [ ] 5.4 Update `get_asset()` and `list_assets()` response handling to include `columns` and `cached_metadata`

## 6. Tests

- [ ] 6.1 Test asset_type/format enum validation (reject unknown types, unknown formats, invalid combinations)
- [ ] 6.2 Test type-specific properties validation (description required for tables, rejection without it)
- [ ] 6.3 Test parquet metadata extraction (column schema, row count, size populated in cached_metadata and asset_columns)
- [ ] 6.4 Test delta metadata extraction (delta_version, partition_columns populated)
- [ ] 6.5 Test column annotation merge (annotations applied, mismatch warnings, missing annotations soft warning for root_id columns)
- [ ] 6.6 Test metadata refresh endpoint (updates cached_metadata, preserves declared annotations, handles new/dropped columns)
- [ ] 6.7 Test asset responses include columns and cached_metadata
