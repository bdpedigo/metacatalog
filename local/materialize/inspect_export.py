"""Print the row count, schema, file count, partitions and partition spec of an export.

Run inside the export container:

    just mat-run python /local/inspect_export.py /exports/<datastack>/v<version>/<table>

Each folder under the export path that holds a _delta_log is one output spec.

If a lake has a cavebear partition spec (the cave.partition_spec table property),
the script also checks the spec and recomputes the partition values of a sample of
rows. It exits with 1 if a check fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pyarrow.compute as pc
from deltalake import DeltaTable

SAMPLE_ROWS = 100_000


def lakes(root: Path) -> list[Path]:
    return sorted(path.parent for path in root.rglob("_delta_log") if path.is_dir())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("export_path", type=Path)
    args = parser.parse_args()

    found = lakes(args.export_path)
    if not found:
        print(f"no Delta Lake under {args.export_path}", file=sys.stderr)
        return 1

    status = 0
    for path in found:
        table = DeltaTable(str(path))
        dataset = table.to_pyarrow_dataset()
        print(f"== {path.relative_to(args.export_path)}")
        print(f"   version:    {table.version()}")
        print(f"   rows:       {dataset.count_rows():,}")
        print(f"   files:      {len(table.file_uris())}")
        print(f"   partitions: {table.metadata().partition_columns}")
        print("   schema:")
        for field in dataset.schema:
            print(f"     {field.name}: {field.type}")
        if not check_partition_spec(table, dataset):
            status = 1
    return status


def check_partition_spec(table: DeltaTable, dataset) -> bool:
    """Print the partition spec of ``table``, and check it on a sample of rows."""
    text = table.metadata().configuration.get("cave.partition_spec")
    if text is None:
        print("   partition spec: none")
        return True
    print(f"   partition spec: {text}")
    import cavebear

    try:
        spec = cavebear.partition_spec(table)
    except ValueError as error:
        print(f"   FAILED: the spec does not describe the table: {error}")
        return False

    columns = sorted({f.name for f in spec.fields} | {f.source for f in spec.fields})
    sample = dataset.head(SAMPLE_ROWS, columns=columns)
    expected = spec.partition_arrays(sample.drop_columns([f.name for f in spec.fields]))
    ok = True
    for name, values in expected.items():
        stored = sample.column(name)
        equal = pc.sum(pc.equal(stored, values).fill_null(False)).as_py() or 0
        both_null = pc.sum(pc.and_(pc.is_null(stored), pc.is_null(values))).as_py() or 0
        mismatches = len(stored) - equal - both_null
        counts = pc.value_counts(dataset.to_table(columns=[name]).column(name))
        sizes = counts.field("counts").to_numpy()
        print(
            f"   {name}: {len(sizes)} partitions, rows per partition "
            f"min {sizes.min():,} / mean {sizes.mean():,.0f} / max {sizes.max():,}"
        )
        if mismatches:
            print(f"   FAILED: {mismatches} of {len(stored):,} sampled rows have a wrong {name}")
            ok = False
        else:
            print(f"   {name}: all {len(stored):,} sampled rows match the transform")
    return ok


if __name__ == "__main__":
    sys.exit(main())
