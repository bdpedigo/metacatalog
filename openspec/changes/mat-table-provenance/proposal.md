## Why

Static dumps of materialization tables need to be discoverable as substitutes for live mat queries — specifically so CAVEclient can route versioned queries to static Delta files when available. The current model encodes provenance implicitly (via name conventions) and conflates semantic column type with column origin, making both machine routing and human annotation harder than necessary.

## What Changes

- Add explicit `source_table` field to assets: the materialization table name a static dump was derived from. Required when `source = "materialization"`, null otherwise.
- Remove `kind: "materialization"` from the column kind discriminated union. Column origin is not a semantic type and shouldn't live alongside `segmentation`, `packed_point`, `split_point`.
- Add column links back to `ColumnAnnotation` as a separate `links` field (distinct from `kind`), encoding joinability relationships between columns. The `ColumnLink` shape is still being designed.

- Add `source_table` as a first-class filter on the asset listing endpoint to support CAVEclient routing queries.

## Capabilities

### New Capabilities

<!-- None — all changes are to existing capabilities. -->

### Modified Capabilities

- `asset-registry`: `source_table` field added to asset data model; name reservation requirement removed; `source_table` filter added to listing endpoint
- `column-kind-schema`: `"materialization"` variant removed from the kind discriminated union; column links (`links` field) added to `ColumnAnnotation` as a separate concept
- `table-model`: `source_table` added as a nullable table-level column; `column_annotations` updated to reflect `links` field

## Impact

- `submodules/catalog/src/cave_catalog/models.py` — add `source_table` column to `assets` table
- `submodules/catalog/src/cave_catalog/schemas.py` — update `ColumnAnnotation`, `ColumnKind` discriminated union, asset request/response schemas
- `submodules/catalog/src/cave_catalog/routers/assets.py` — add `source_table` query filter; remove name reservation check
- `submodules/catalog/src/cave_catalog/validation.py` — add `source_table` required-when-source-is-materialization check; remove name reservation logic
- `submodules/catalog/migrations/` — new Alembic migration for `source_table` column
- `submodules/catalog/tests/` — update annotation and registration tests
- CAVEclient (future): routing logic queries `source_table + mat_version` to find available static copies
