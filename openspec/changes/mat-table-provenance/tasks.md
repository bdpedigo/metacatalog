## 1. Data Model & Schemas

- [ ] 1.1 Add `source_table: str | None` to the SQLAlchemy `Asset` model (alongside existing table-specific nullable columns)
- [ ] 1.2 Remove `MaterializationKind` variant from the `ColumnKind` discriminated union in `schemas.py`
- [ ] 1.3 Add `ColumnLink` Pydantic model (`link_type: Literal["copy", "join"]`, `target_table: str`, `target_column: str | None`)
- [ ] 1.4 Add `links: list[ColumnLink]` field to `ColumnAnnotation` schema (default empty list)
- [ ] 1.5 Add `source_table` to asset request and response schemas

## 2. Validation Logic

- [ ] 2.1 Add validation: `source_table` required when `source == "materialization"`, null otherwise
- [ ] 2.2 Update column annotation validation to remove materialization kind validation path; add `link_type` enum validation

## 3. API

- [ ] 3.1 Add `source_table` as an optional query parameter to `GET /api/v1/assets/` listing endpoint
- [ ] 3.2 Apply `source_table` filter in the listing query when parameter is provided
- [ ] 3.3 Ensure `source_table` is returned in all asset response shapes that include table-specific fields

## 4. Read-time Column Merging

- [ ] 4.1 Update the column merge logic to include `kind` and `links` fields in the merged column response

## 5. Frontend (Templates)

- [ ] 5.1 `explore_detail.html`: add `Source Table` row to the summary card (display only, alongside existing `Source` row)
- [ ] 5.2 `explore_detail.html`: replace the `"materialization"` kind branch in the Columns table with a `Links` column that renders `"copy"` and `"join"` badges (e.g. `copy → synapses.root_id`)
- [ ] 5.3 `explore_edit.html`: remove `<option value="materialization">` from the kind dropdown and its corresponding `{% if col.kind.kind == "materialization" %}` inline fields block
- [ ] 5.4 `explore_edit.html`: remove `<template id="mat-fields-template">` and any JS referencing it
- [ ] 5.5 `explore_edit.html`: add read-only display of existing links per column row (links are auto-populated by the export workflow; no add/edit UI needed for now)

## 6. Tests

- [ ] 6.1 Update asset registration tests: add `source_table` required-for-mat scenarios
- [ ] 6.2 Add tests for `source_table` listing filter
- [ ] 6.3 Update column annotation tests: remove materialization kind scenarios, add `"copy"` and `"join"` link scenarios
- [ ] 6.4 Add test: column annotation with both `kind` and `links` populated independently
- [ ] 6.5 Update column merge tests to include `kind` and `links` in merged output shape
