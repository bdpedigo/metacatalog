# %%

import time

import numpy as np
import polars as pl
from deltalake import DeltaTable, write_deltalake
from deltalake.table import TableOptimizer
from deltalake.writer import BloomFilterProperties, ColumnProperties, WriterProperties

base_table = pl.scan_delta(
    "/Users/ben.pedigo/code/meshrep/meshrep/data/synapses_pni_2_v1412_deltalake"
)

base_table.collect_schema()


# %%


output_specs = {
    # vary number of partitions, with percentile range partitioning, z-ordering, and bloom filters on post_pt_root_id
    "post_pt_root_id-256": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 256,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.01,
        "target_file_size_mb": 100,
    },
    "post_pt_root_id-1024": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 1024,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.01,
        "target_file_size_mb": 100,
    },
    "post_pt_root_id-4096": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 4096,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.01,
        "target_file_size_mb": 100,
    },
    "post_pt_root_id-8192": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 8192,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.01,
        "target_file_size_mb": 100,
    },
    # use hash partitioning on post_pt_root_id with 1024 partitions, z-ordering, and bloom filters
    "post_pt_root_id-1024-hash": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "hash",
        "n_partitions": 1024,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.01,
        "target_file_size_mb": 100,
    },
    # now drop bloom filters
    "post_pt_root_id-1024-no-bloom": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 1024,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": [],
        "bloom_filter_fpp": None,
        "target_file_size_mb": 100,
    },
    # finer bloom
    "post_pt_root_id-1024-finer-bloom": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 1024,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.001,
        "target_file_size_mb": 100,
    },
}


# %%
## compute partition boundaries for each spec and add them to the spec dict

currtime = time.time()

all_n_partitions = set(spec["n_partitions"] for spec in output_specs.values())

col_data = base_table.select("post_pt_root_id").collect()["post_pt_root_id"].unique()

partition_bounds = {
    n_partitions: col_data.quantile(
        list(np.linspace(0, 1, n_partitions - 1)), interpolation="nearest"
    )
    for n_partitions in all_n_partitions
}

print(f"{time.time() - currtime:.3f} seconds elapsed.")


# %%
def prep_table_for_write(table, spec):
    if spec["partition_strategy"] == "percentile_range":
        bounds = partition_bounds[spec["n_partitions"]]
        return table.with_columns(
            pl.col(spec["partition_by"])
            .cut(breaks=bounds, labels=np.arange(spec["n_partitions"]).astype(str))
            .cast(pl.Int32)
            .alias(spec["partition_by"] + "_partition")
        )
    elif spec["partition_strategy"] == "hash":
        return table.with_columns(
            (pl.col(spec["partition_by"]).hash() % spec["n_partitions"]).alias(
                spec["partition_by"] + "_partition"
            )
        )
    return table


# %%


base_out_path = "gs://allen-minnie-phase3/bdp-synapse-mega-tables/deltalake-comparisons"
n_rows_per_chunk = 25_000_000
write_mode = "append"


def get_written_row_count(path: str) -> int:
    try:
        dt = DeltaTable(path)
        actions = dt.get_add_actions(flatten=True)
        return sum(actions.column("num_records").to_pylist())
    except Exception:
        return 0


# Determine per-spec how many source rows have already been written
spec_row_offsets = {
    spec_name: get_written_row_count(base_out_path + f"/{spec_name}")
    for spec_name in output_specs
}
print("Existing row counts per spec:", spec_row_offsets)


#%%
# Start from the earliest unfinished chunk boundary across all specs
start = (min(spec_row_offsets.values()) // n_rows_per_chunk) * n_rows_per_chunk


while True:
    print(f"Processing chunk for rows {start:,} to {start + n_rows_per_chunk:,}...")
    chunk_table = base_table.slice(start, n_rows_per_chunk).collect()

    if chunk_table.is_empty():
        break

    for spec_name, spec in output_specs.items():
        if start < spec_row_offsets[spec_name]:
            print(f"  Skipping {spec_name} at offset {start:,} (already written)")
            continue
        out_path = base_out_path + f"/{spec_name}"
        print(f"  Writing chunk to {out_path} with spec {spec_name}...")
        spec_table = prep_table_for_write(chunk_table, spec)
        write_deltalake(
            out_path,
            spec_table,
            partition_by=spec["partition_by"] + "_partition",
            mode=write_mode,
            writer_properties=WriterProperties(compression="SNAPPY"),
            target_file_size=spec["target_file_size_mb"] * 1024 * 1024,
        )

    start += n_rows_per_chunk

# %%
# currtime = time.time()
# test_table_count = (
#     pl.scan_delta(base_out_path + "/post_pt_root_id-1024").select(pl.len()).collect()
# )
# print(f"{time.time() - currtime:.3f} seconds elapsed.")


# %%
optimize_time = time.time()


def optimize_deltalake(path, zorder_columns, bloom_filter_columns, fpp):
    if len(bloom_filter_columns) > 0:
        bloom = BloomFilterProperties(
            set_bloom_filter_enabled=True,
            fpp=fpp,
        )
        column_properties = ColumnProperties(bloom_filter_properties=bloom)
        writer_properties = WriterProperties(
            column_properties={col: column_properties for col in bloom_filter_columns}
        )
    else:
        writer_properties = None

    dt = DeltaTable(path)
    to = TableOptimizer(dt)
    to.z_order(columns=zorder_columns, writer_properties=writer_properties)
    dt.vacuum(
        dry_run=False, retention_hours=0, enforce_retention_duration=False, full=True
    )


for spec_name, spec in output_specs.items():
    print(f"Optimizing {spec_name}...")
    optimize_deltalake(
        base_out_path + f"/{spec_name}",
        zorder_columns=spec["zorder_columns"],
        bloom_filter_columns=spec["bloom_filter_columns"],
        fpp=spec["bloom_filter_fpp"],
    )
