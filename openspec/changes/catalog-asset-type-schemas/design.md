## Context

The catalog service currently stores assets with a flat schema: core identity fields plus a freeform `properties` JSON blob. `asset_type` and `format` are free strings with no validation beyond presence. The format sniff pipeline validates that a URI matches the claimed format but does not extract metadata.

This design covers adding type-specific metadata schemas, a column metadata model for tables, and a metadata extraction pipeline — all aimed at making the catalog a governance layer that enforces documentation of what assets are and how they relate to each other.

The catalog is early-stage with no production users, so backward compatibility and migration complexity are non-concerns. The dataset is small (hundreds to low thousands of assets), so query performance is not a driver — governance and discoverability are.

## Goals / Non-Goals

**Goals:**
- Enforce `asset_type` and `format` as controlled vocabularies
- Define a registry pattern where each `(asset_type, format)` pair maps to a validation schema and metadata extractor
- Require table-type assets to have column metadata, combining derived (from file) and declared (from registrant) information
- Support column-level annotations: descriptions, cross-table references, semantic types, units
- Extract and store system-derived metadata (row counts, column schemas, size) at registration time
- Support on-demand metadata refresh for mutable assets

**Non-Goals:**
- Support for non-table asset types (image volumes, meshes, etc.) — the design should accommodate them but not implement them
- Real-time synchronization of cached metadata with underlying files
- Column-level search/query optimization (GIN indexes, join tables for column lookup) — can add later if needed
- Schema evolution tracking (detecting when a table's columns change across revisions)

## Decisions

### Decision 1: `(asset_type, format)` as a composite discriminator

Each asset's metadata profile is determined by the combination of `asset_type` and `format`, not either alone. A parquet table and a delta table share most table metadata but differ in format-specific fields (delta has partition columns, version info). A delta table and a hypothetical delta-backed annotation layer would differ in type-specific fields.

The registry maps `(asset_type, format)` → `(PropertiesSchema, MetadataExtractor)`.

**Alternative considered**: Discriminate on `asset_type` alone with format as a sub-field. Rejected because format drives real differences in both what can be extracted and what metadata is meaningful (e.g., delta partition columns).

### Decision 2: Composition via base + format extension for properties schemas

Table-type schemas use inheritance: `TableBaseProperties` defines shared fields (source, description) and `DeltaTableProperties(TableBaseProperties)` adds format-specific declared fields. This avoids duplicating field definitions across parquet/delta/lance while keeping each combination explicit.

```
TableBaseProperties
├── source: str | None
├── source_table: str | None
├── description: str          ← REQUIRED for tables
└── ...provenance fields

DeltaTableProperties(TableBaseProperties)
└── (no extra declared fields currently — delta-specific info is derived)

ParquetTableProperties(TableBaseProperties)
└── (same — parquet-specific info is derived)
```

In practice, for the near-term (parquet, delta, lance), the format extensions may add no extra declared fields — the format differences show up in derived metadata, not user declarations.

### Decision 3: Separate `cached_metadata` column for system-derived data

A new `cached_metadata` JSONB column on the `assets` table stores metadata extracted from the underlying file: `n_rows`, `n_columns`, `size_bytes`, `column_schema` (names + types + nullability), plus format-specific fields like `delta_version` and `partition_columns`.

A `metadata_cached_at` timestamp tracks freshness. A refresh endpoint allows re-extraction.

**Rationale**: Separating derived from declared metadata gives a clean ownership boundary. `properties` is user-controlled and validated at registration. `cached_metadata` is system-managed and refreshable. You can blow away and re-derive `cached_metadata` without touching user data.

**Alternative considered**: Storing everything in `properties`. Rejected because it conflates user intent with system-derived state, making refresh semantics ambiguous.

### Decision 4: `asset_columns` table for per-column declared metadata

A separate `asset_columns` table stores per-column metadata combining derived info (name, type, nullable, ordinal position from the file) with user-declared annotations (description, references, semantic_type, unit).

```
asset_columns
├── asset_id: UUID FK → assets.id ON DELETE CASCADE
├── column_name: text
├── column_type: text         ← derived from file
├── nullable: bool            ← derived from file
├── ordinal: int              ← derived from file
├── description: text | NULL  ← declared by registrant
├── semantic_type: text | NULL
├── unit: text | NULL
├── ref_table: text | NULL    ← references another table/asset
├── ref_column: text | NULL
├── ref_datastack: text | NULL
├── ref_relationship: text | NULL  (foreign_key | derived | lookup)
└── PRIMARY KEY (asset_id, column_name)
```

**Rationale**: Columns have structured, mixed-provenance data that is genuinely relational. A JSON array inside `cached_metadata` would work for derived schema but makes declared annotations awkward — you'd need to merge user-supplied column annotations with derived column info inside a JSON blob. A real table gives clear per-column identity for both derived and declared fields.

**Alternative considered**: JSON array in `cached_metadata`. Rejected because column annotations (descriptions, references) are user-declared, not system-derived, and don't belong in `cached_metadata`. Having them in a real table also opens future column-level querying without schema changes.

### Decision 5: Metadata extractors replace format sniffers

The existing `FORMAT_SNIFFERS` registry evolves into a `METADATA_EXTRACTORS` registry keyed by `(asset_type, format)`. Each extractor validates the format (the sniff) AND extracts metadata in one pass. For tables, this means reading the parquet footer / delta log / lance manifest to get column schema, row count, and format-specific info.

```python
METADATA_EXTRACTORS: dict[tuple[str, str], MetadataExtractor] = {
    ("table", "parquet"): extract_parquet_table,
    ("table", "delta"): extract_delta_table,
    ("table", "lance"): extract_lance_table,
}
```

Each extractor returns a structured result: `ExtractionResult(cached_metadata: dict, column_schema: list[ColumnInfo], validation: ValidationCheck)`. The validation check replaces the old format sniff check.

### Decision 6: Column annotation merging at registration

At registration, the pipeline:
1. Runs the metadata extractor → gets derived column schema (names, types, nullability)
2. Accepts optional column annotations from the registrant (description, references, semantic_type, unit) keyed by column name
3. Merges: for each derived column, overlays any matching declared annotations
4. Warns if the registrant declared annotations for columns that don't exist in the file
5. Stores merged results in `asset_columns`

The registrant's column declarations in the request body:
```json
{
  "column_annotations": {
    "pre_pt_root_id": {
      "description": "Root ID of the presynaptic neuron",
      "references": {
        "table": "nucleus_detection_v0",
        "column": "pt_root_id",
        "relationship": "lookup"
      },
      "semantic_type": "root_id"
    }
  }
}
```

### Decision 7: Enforcement levels for table metadata

- **Required**: `description` field in properties (a short description of the table)
- **Required**: Column schema extraction must succeed (the file must be readable)
- **Soft enforcement**: Warn (in validation report) when `*_root_id` columns on mat-sourced tables lack a `references` declaration — but don't block registration
- **Optional**: Column descriptions, semantic types, units — validated if provided, not required

This balances governance (force people to describe their table) with friction (don't block someone from registering because they haven't annotated every column yet). Column annotations can be added incrementally via a future update endpoint.

### Decision 8: Controlled vocabularies for `asset_type` and `format`

`asset_type` becomes a Python `StrEnum` with `table` as the initial value. `format` becomes a per-type enum: `TableFormat` with `parquet`, `delta`, `lance`. The API rejects unknown values.

Future types (image_volume, mesh, etc.) add new enum values and their own format enums. The `(asset_type, format)` registry acts as the source of truth for what combinations are valid.

## Risks / Trade-offs

**[Column annotation friction]** → Requiring any annotations at registration adds friction. Mitigation: only `description` at the table level is required; column annotations are optional and can be added later.

**[Extractor failures blocking registration]** → If a metadata extractor fails (network issue reading file, unsupported parquet variant), it blocks registration. Mitigation: extractor failure returns a clear validation error; the registrant can fix the file or format issue.

**[Schema drift for mutable assets]** → A delta table may gain columns over time but `asset_columns` reflects the schema at registration. Mitigation: the refresh endpoint re-extracts and updates `asset_columns` derived fields. Declared annotations for dropped columns are preserved but flagged.

**[Lance extractor availability]** → Lance is newer and its metadata API may be less stable. Mitigation: lance support can start with basic schema extraction and add richer metadata as the library matures.

## Open Questions

- Should there be a `PATCH /api/v1/assets/{id}/columns` endpoint for updating column annotations after registration, or should it require re-registration?
- Should the validation report include "soft warnings" (missing column references) separately from hard failures, and if so, what does the report structure look like?
- For the `references` field, should the catalog validate that the referenced table/asset actually exists at registration time?
