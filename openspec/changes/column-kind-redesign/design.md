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

class PackedPointKind(BaseModel):
    kind: Literal["packed_point"]
    resolution: list[float] | None = None  # must be length 3 when set [rx, ry, rz]

class SplitPointKind(BaseModel):
    kind: Literal["split_point"]
    axis: Literal["x", "y", "z"]  # required
    point_group: str | None = None
    resolution: float | None = None  # scalar resolution for this axis

ColumnKind = Annotated[
    MatKind | SegmentationKind | PackedPointKind | SplitPointKind,
    Field(discriminator="kind"),
]
```

**Rationale**: Spatial data comes in two common forms — packed (single column with all xyz, e.g., `pt_position` as array/struct) and split (separate columns for each axis, e.g., `pt_position_x`, `_y`, `_z`). These have different semantics:
- **Packed**: one column has all coordinates; resolution is a 3-vector.
- **Split**: each column is a single axis; `axis` is required; `point_group` ties columns together; resolution is a scalar per-axis.

Each kind needs different fields. A discriminated union enforces this at the type level and serializes cleanly to/from JSON. The `kind` discriminator maps directly to the UI selector.

**Alternative considered**: A single `PointKind` with optional `axis`. Rejected because it conflates packed vs. split semantics and makes `axis` optionality confusing (optional for packed, required for split).

### 2. Singular `kind` field (not a list)

```python
class ColumnAnnotation(BaseModel):
    column_name: str
    description: str | None = None
    kind: ColumnKind | None = None
```

**Rationale**: Kind types are mutually exclusive for a column. A root_id column is a segmentation kind — it doesn't also need a materialization kind since the segmentation kind subsumes the join semantics. Singular is simpler for the UI (one selector, not a list builder).

**Migration to list later**: Trivial — one Alembic migration wrapping `kind` → `kinds: [kind]`, Pydantic change, UI update.

### 3. `point_group` for spatial column grouping (split points only)

Split point columns often come as `x`, `y`, `z` in separate columns. The `point_group` string (e.g., `"pt_position"`) ties them together without introducing a complex grouping model. A uniqueness constraint ensures no two columns in a table share the same `(point_group, axis)` pair.

**Rationale**: Lightweight. Consumers discover groups by matching `point_group` values. No need for a separate group entity or ordering logic. The uniqueness check prevents ambiguous group membership.

### 4. Validation dispatch on kind

- `materialization` → validate `target_table` exists in ME (existing logic); form options are already generated from available tables/columns so invalid targets are constrained at the UI level
- `segmentation` → validate node_level matches pattern: `root_id`, `supervoxel_id`, or `level\d+_id`; validate column dtype is integer (int8–int64, uint8–uint64)
- `packed_point` → validate column dtype is numeric (int or float); validate resolution list has exactly 3 elements when provided
- `split_point` → validate `axis` is required; validate column dtype is numeric; validate `(point_group, axis)` uniqueness across annotations

**dtype validation**: When cached metadata is available, kind assignment is checked against `ColumnInfo.dtype` for the target column:
- `segmentation` requires integer dtype (node IDs are always ints)
- `packed_point` / `split_point` require numeric dtype (coordinates are int or float)
- `materialization` has no dtype constraint (foreign keys can be any type that matches the target)

If cached metadata is not yet available (e.g., metadata extraction hasn't run), dtype validation is skipped — the kind is accepted optimistically and can be re-validated later.

**Rationale**: These checks catch obvious mistakes at registration time (e.g., assigning segmentation kind to a string column) without requiring external service calls. Materialization validation remains the only kind that hits an external API.

## Risks / Trade-offs

- **Breaking API change** → Mitigated by data migration and versioned rollout. Existing annotation data maps cleanly to `MatKind` (set `kind` to `"materialization"`, keep `target_table`/`target_column`).
- **Singular kind limits future flexibility** → Accepted trade-off. Migration to list is low-cost given JSONB storage.
- **`point_group` is convention-based** → No enforcement that a group has all 3 axes. Acceptable for v1; could add validation later.
- **New kind types require code changes** → By design. Each kind has distinct validation and UI behavior, so they should be explicit rather than fully dynamic.
