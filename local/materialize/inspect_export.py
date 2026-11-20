"""Print the row count, schema, file count and partition columns of an export.

Run inside the export container:

    just mat-run python /local/inspect_export.py /exports/<datastack>/v<version>/<table>

Each folder under the export path that holds a _delta_log is one output spec.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deltalake import DeltaTable


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
    return 0


if __name__ == "__main__":
    sys.exit(main())
