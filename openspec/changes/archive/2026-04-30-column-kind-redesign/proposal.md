## Why

The current column annotation schema (`ColumnLink` with `link_type: "foreign_key" | "join"`, `target_table`, `target_column`) only supports connections to materialization service tables. The `foreign_key` vs `join` distinction is unused and semantically unclear. In practice, columns also connect to the chunkedgraph (root IDs, level2 IDs, supervoxel IDs) and represent spatial coordinates. These are fundamentally different *kinds* of columns that require different metadata, and they are mutually exclusive per column.

## What Changes

- **BREAKING**: Replace the flat `ColumnLink` model with a discriminated union `ColumnKind = MatKind | SegmentationKind | PointKind` keyed on a `kind` field.
- Remove the `"foreign_key"` / `"join"` distinction — materialization kinds just connect to a table+column.
- Add `SegmentationKind` for columns containing chunkedgraph node IDs (root, level2, supervoxel).
- Add `PointKind` for spatial coordinate columns, with `axis` and `point_group` fields.
- Change `ColumnAnnotation.links` (list) to `ColumnAnnotation.kind: ColumnKind | None` (singular, since kind types are mutually exclusive per column).
- Update UI to show a kind selector that conditionally renders variant-specific fields.
- Update validation to dispatch on kind (only materialization kinds need ME validation).

## Capabilities

### New Capabilities
- `column-kind-schema`: Discriminated union schema for column kinds (MatKind, SegmentationKind, PointKind) with variant-specific fields and validation.

### Modified Capabilities
- `table-column-annotations`: Annotations change from flat `links` list to `kind: ColumnKind | None` (discriminated union, singular). Validation rules change per variant.
- `table-registration-ui`: UI changes from a single dropdown to a kind selector with conditional sub-fields.

## Impact

- **Backend models**: `cave_catalog/table_schemas.py` — full rewrite to kind models
- **Validation**: `cave_catalog/validation.py` — dispatch on kind, only validate mat kinds against ME
- **Database**: Migration to reshape existing `column_annotations` JSONB (convert old `links` list to singular `kind`, set `kind` field to `"materialization"`)
- **UI templates**: `register.html`, `explore_edit.html` — new conditional form sections
- **API contracts**: Request/response shape changes for annotation endpoints
- **Tests**: `test_link_validation.py`, `test_tables.py` — update for new schema
