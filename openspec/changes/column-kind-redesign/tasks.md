## 1. Schema & Models

- [ ] 1.1 Replace old `ColumnLink` with discriminated union (`MatKind`, `SegmentationKind`, `PointKind`) in `table_schemas.py`
- [ ] 1.2 Change `ColumnAnnotation.links` to `ColumnAnnotation.kind: ColumnKind | None`
- [ ] 1.3 Update `MergedColumn` model to use singular `kind` field
- [ ] 1.4 Add unit tests for new Pydantic models (each variant, invalid combinations)

## 2. Validation

- [ ] 2.1 Refactor validation to dispatch on `kind` (only validate materialization kinds against ME)
- [ ] 2.2 Add dtype validation for kind assignment (segmentation requires int; point requires int or float; skip if no cached metadata)
- [ ] 2.3 Update validation tests for new schema (mat kinds validated, seg/point dtype checks, skip when metadata absent)

## 3. API & Endpoints

- [ ] 3.1 Update `POST /api/v1/tables/register` to accept new annotation shape
- [ ] 3.2 Update `PATCH /api/v1/tables/{id}/annotations` to accept new annotation shape
- [ ] 3.3 Update table response serialization for singular `kind` field
- [ ] 3.4 Update `test_tables.py` registration/annotation tests for new kind shape
- [ ] 3.5 Add integration test for segmentation kind round-trip (no ME validation)
- [ ] 3.6 Add integration test for point kind round-trip with point_group

## 4. UI Updates

- [ ] 4.1 Update registration form to show kind selector (Materialization / Segmentation / Point)
- [ ] 4.2 Implement conditional field rendering per kind variant
- [ ] 4.3 Update explore/edit page kind editing for new schema
- [ ] 4.4 Update `linkable-targets` and `target-columns` fragment endpoints (materialization-only, gated on kind selection)
