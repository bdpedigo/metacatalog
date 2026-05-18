## Context

The catalog service stores assets with a `source` field (`"user"` | `"materialization"`) and a `mat_version` integer, but no explicit field identifying *which* materialization table an asset is a copy of. Convention uses `name ≈ source_table` for simple cases, but this breaks for layout variants (e.g., `synapses.by_position`). The column kind schema includes a `"materialization"` variant that encodes column origin alongside semantic types (`"segmentation"`, `"packed_point"`, `"split_point"`), conflating two orthogonal concerns. CAVEclient routing — switching a versioned query to a static Delta file when one is available — requires querying assets by `(datastack, source_table, mat_version)`, which is not currently possible.

## Goals / Non-Goals

**Goals:**
- Make `source_table` a first-class queryable field on assets
- Separate column semantic type (kind) from column origin (links)
- Remove name reservation logic that is no longer load-bearing
- Define the shape of `ColumnLink` well enough to implement, while acknowledging the design may evolve

**Non-Goals:**
- CAVEclient routing implementation — this change is catalog-side only
- Enforcing link validity against the mat service at write time (deferred)
- Supporting multi-source column provenance (e.g., a packed point derived from three separate source columns) — `source_column` is nullable for these cases

## Decisions

### 1. `source_table` as a nullable column on `assets`

**Decision**: Add `source_table` (TEXT, nullable) to the `assets` table alongside the existing `source` and `mat_version` columns. Required (validated at application layer) when `source = "materialization"`, null otherwise. No new table or type hierarchy needed.

**Alternatives considered**:
- Store in `properties` JSONB — already used for asset-type-specific fields, but `source_table` is a first-class filter key, so it needs to be a real indexed column for routing queries.
- Infer from `name` — the current implicit convention. Breaks for layout variants and is opaque to query engines.

**Rationale**: Consistent with existing nullable column pattern (`format`, `mat_version`). Keeps the schema flat and queryable without a migration to a separate table.

### 2. Remove `kind: "materialization"` from the column kind union

**Decision**: The `"materialization"` variant is removed from the `ColumnKind` discriminated union. Column origin (where a value came from) is not a semantic type. The kind union is purely semantic: `"segmentation"` | `"packed_point"` | `"split_point"` | null.

**Alternatives considered**:
- Keep `"materialization"` as a kind and add provenance separately — results in two mechanisms encoding the same information; confusing at write time.
- Allow multiple kinds per column — rejected earlier; kinds are mutually exclusive semantic types.

**Rationale**: Cleaner separation. The export workflow needs to express both "this is a root ID" and "this came from synapses.root_id" — these are different annotation layers. Conflating them into one `kind` field forces a choice between the two.

### 3. Column links as a separate `links` field on `ColumnAnnotation`

**Decision**: Add `links: list[ColumnLink]` to `ColumnAnnotation` alongside `kind`. A `ColumnLink` encodes a joinable relationship between this column and a column in a materialization table.

**ColumnLink shape**:
```
ColumnLink:
  link_type: "copy" | "join"
  target_table: str       # mat table name within the same datastack
  target_column: str | None  # null for computed/merged columns
```

`"copy"` means value-equivalent: the values in this column are the same as `target_table.target_column`, so CAVEclient routing can substitute this static dump for a live mat query. `"copy"` also implies a valid join. `"join"` means a join is valid but the values are not a direct copy — used for foreign-key style relationships in enriched/derived tables.

**Alternatives considered**:
- Encode via kind — rejected (see Decision 2).
- No links, just `source_table` at asset level — sufficient for routing but loses column-level joinability information needed for cross-table queries and UI linking.

**Rationale**: Links answer "what can I join on" — a query-planning concern separate from semantic type. The export workflow auto-populates links for mat dumps; humans can add them for derived/enriched tables.

## Risks / Trade-offs

- **ColumnLink field set may grow** → Additional fields (e.g., cardinality hints, directionality) could be added later. JSONB storage means no migration is needed for additive changes, but backfilling may be required if semantics shift.
- **`source_table` requires a migration** → Adds a nullable column; straightforward additive migration with no downtime risk. Existing mat-sourced assets will have `source_table = null` until backfilled by the export workflow on next run.
## Open Questions

- **Link validation at write time**: Should the catalog validate that `target_table` exists in the mat service when a link is submitted? Currently deferred (no external call for links), but worth revisiting once CAVEclient starts consuming links.
- **Backfill strategy**: When should existing mat dump assets have `source_table` populated? On next export run, or via a one-time migration script?
