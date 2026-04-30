## Context

Column annotations currently store links as a flat list of `ColumnLink(link_type, target_table, target_column)` in a JSONB column on the `Asset` table. The `link_type` field accepts `"foreign_key"` or `"join"` but both behave identically. All links assume the target is a materialization service table.

In practice, columns in CAVE tables connect to three distinct systems:
1. **Materialization service** — join to a specific table/column (e.g., `synapses.id`)
2. **Chunkedgraph** — root IDs, level2 IDs, or supervoxel IDs that reference segmentation
3. **Spatial coordinate system** — positions in nm

These are mutually exclusive: a root_id column doesn't meaningfully "join" to a single mat table — it joins to *any* table with root IDs. Its semantic meaning is its connection to the chunkedgraph.

## Goals / Non-Goals

**Goals:**
- Replace the undifferentiated model with a discriminated union that captures variant-specific metadata
- Support materialization, segmentation, and spatial point kind types
- Keep the schema simple and extensible (easy to add new kinds or cardinality later)
- Singular kind per column (mutually exclusive types)

**Non-Goals:**
- Cardinality annotations (m:1, 1:m, m:m) — deferred to future work
- Multi-kind per column — deferred; current model uses singular, migration to list is trivial since storage is JSONB
- Auto-inference of kind from column names — out of scope
- Validation of segmentation/point kinds against external services — only mat kinds are validated

## Decisions

### 1. Discriminated union on `kind` field

```python
class MatKind(BaseModel):
    kind: Literal["materialization"]
    target_table: str
    target_column: str

class SegmentationKind(BaseModel):
    kind: Literal["segmentation"]
    node_level: str  # "root_id", "supervoxel_id", or "level{N}_id" (e.g., "level2_id")

class PointKind(BaseModel):
    kind: Literal["point"]
    axis: Literal["x", "y", "z"] | None = None
    point_group: str | None = None

ColumnKind = Annotated[MatKind | SegmentationKind | PointKind, Field(discriminator="kind")]
```

**Rationale**: Each kind needs different fields. A discriminated union enforces this at the type level and serializes cleanly to/from JSON. The `kind` discriminator maps directly to the UI selector.

**Alternative considered**: A single model with many optional fields. Rejected because it allows invalid combinations and makes validation more complex.

### 2. Singular `kind` field (not a list)

```python
class ColumnAnnotation(BaseModel):
    column_name: str
    description: str | None = None
    kind: ColumnKind | None = None
```

**Rationale**: Kind types are mutually exclusive for a column. A root_id column is a segmentation kind — it doesn't also need a materialization kind since the segmentation kind subsumes the join semantics. Singular is simpler for the UI (one selector, not a list builder).

**Migration to list later**: Trivial — one Alembic migration wrapping `kind` → `kinds: [kind]`, Pydantic change, UI update.

### 3. `point_group` for spatial column grouping

Spatial coordinates often come as `x`, `y`, `z` in separate columns. The `point_group` string (e.g., `"pt_position"`) ties them together without introducing a complex grouping model.

**Rationale**: Lightweight. Consumers discover groups by matching `point_group` values. No need for a separate group entity or ordering logic.

### 4. Validation dispatch on kind

- `materialization` → validate `target_table` exists in ME (existing logic)
- `segmentation` → validate node_level matches pattern: `root_id`, `supervoxel_id`, or `level\d+_id`
- `point` → no external validation needed (axis is enum-constrained)

**Rationale**: Only mat kinds reference external state that can be invalid. Segmentation and point kinds are self-describing (node_level validated by regex pattern, axis by enum).

## Risks / Trade-offs

- **Breaking API change** → Mitigated by data migration and versioned rollout. Existing annotation data maps cleanly to `MatKind` (set `kind` to `"materialization"`, keep `target_table`/`target_column`).
- **Singular kind limits future flexibility** → Accepted trade-off. Migration to list is low-cost given JSONB storage.
- **`point_group` is convention-based** → No enforcement that a group has all 3 axes. Acceptable for v1; could add validation later.
- **New kind types require code changes** → By design. Each kind has distinct validation and UI behavior, so they should be explicit rather than fully dynamic.
