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
    # "post_pt_root_id-256": {
    #     "partition_by": "post_pt_root_id",
    #     "partition_strategy": "percentile_range",
    #     "n_partitions": 256,
    #     "zorder_columns": ["post_pt_root_id"],
    #     "bloom_filter_columns": ["post_pt_root_id"],
    #     "bloom_filter_fpp": 0.01,
    #     "target_file_size_mb": 100,
    # },
    "post_pt_root_id-1024-range": {
        "partition_by": "post_pt_root_id",
        "partition_strategy": "percentile_range",
        "n_partitions": 1024,
        "zorder_columns": ["post_pt_root_id"],
        "bloom_filter_columns": ["post_pt_root_id"],
        "bloom_filter_fpp": 0.01,
        "target_file_size_mb": 100,
    },
    # "post_pt_root_id-4096": {
    #     "partition_by": "post_pt_root_id",
    #     "partition_strategy": "percentile_range",
    #     "n_partitions": 4096,
    #     "zorder_columns": ["post_pt_root_id"],
    #     "bloom_filter_columns": ["post_pt_root_id"],
    #     "bloom_filter_fpp": 0.01,
    #     "target_file_size_mb": 100,
    # # },
    # "post_pt_root_id-8192": {
    #     "partition_by": "post_pt_root_id",
    #     "partition_strategy": "percentile_range",
    #     "n_partitions": 8192,
    #     "zorder_columns": ["post_pt_root_id"],
    #     "bloom_filter_columns": ["post_pt_root_id"],
    #     "bloom_filter_fpp": 0.01,
    #     "target_file_size_mb": 100,
    # },
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
    # "post_pt_root_id-1024-no-bloom": {
    #     "partition_by": "post_pt_root_id",
    #     "partition_strategy": "percentile_range",
    #     "n_partitions": 1024,
    #     "zorder_columns": ["post_pt_root_id"],
    #     "bloom_filter_columns": [],
    #     "bloom_filter_fpp": None,
    #     "target_file_size_mb": 100,
    # },
    # finer bloom
    # "post_pt_root_id-1024-finer-bloom": {
    #     "partition_by": "post_pt_root_id",
    #     "partition_strategy": "percentile_range",
    #     "n_partitions": 1024,
    #     "zorder_columns": ["post_pt_root_id"],
    #     "bloom_filter_columns": ["post_pt_root_id"],
    #     "bloom_filter_fpp": 0.001,
    #     "target_file_size_mb": 100,
    # },
}


# %%
## compute partition boundaries for each spec and add them to the spec dict

currtime = time.time()

all_n_partitions = set(spec["n_partitions"] for spec in output_specs.values())

col_data = base_table.select("post_pt_root_id").collect()["post_pt_root_id"].unique()

partition_bounds = {
    n_partitions: col_data.quantile(
        list(np.linspace(0, 1, n_partitions + 1)[1:-1]), interpolation="nearest"
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
            .cast(pl.String)
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

# %%
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


# %%
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


# %%
finished = [
    # "post_pt_root_id-256",
    "post_pt_root_id-1024-hash",
]

for spec_name, spec in output_specs.items():
    if spec_name in finished:
        print(f"Skipping optimization for {spec_name} (already optimized)")
        continue
    print(f"Optimizing {spec_name}...")
    optimize_deltalake(
        base_out_path + f"/{spec_name}",
        zorder_columns=spec["zorder_columns"],
        bloom_filter_columns=spec["bloom_filter_columns"],
        fpp=spec["bloom_filter_fpp"],
    )

# %%
from pathlib import Path

import pandas as pd

version = 1412
TABLE_CACHE_PATH = Path("/Users/ben.pedigo/code/meshrep/meshrep/data/table_cache")

query_args = dict(desired_resolution=[1, 1, 1], split_positions=True)

table_path = TABLE_CACHE_PATH / f"v{version}" / "aibs_cell_info.csv.gz"
if table_path.exists():
    cell_info = pd.read_csv(table_path, index_col=0)


# %%
query_cell_info = cell_info.query("broad_type == 'inhibitory'").copy()
print(len(query_cell_info), "inhibitory neurons")

import polars as pl


def synapse_query(table_spec_name, table_spec, post_ids=None, partition_plan=True):
    table_path = base_out_path + f"/{table_spec_name}"
    table = pl.scan_delta(table_path)

    post_list = [post_ids] if isinstance(post_ids, (int,)) else list(post_ids)

    if partition_plan:
        query_table = pl.DataFrame({"post_pt_root_id": post_list})
        query_table = prep_table_for_write(query_table, table_spec)

        table = table.filter(
            pl.col("post_pt_root_id").is_in(query_table["post_pt_root_id"].to_list()),
            pl.col("post_pt_root_id_partition").is_in(
                query_table[table_spec["partition_by"] + "_partition"].to_list()
            ),
        )
    else:
        table = table.filter(pl.col("post_pt_root_id").is_in(post_list))

    return table.collect(engine="streaming")


# from tqdm.auto import trange

rows = []

n_trials = 10
n_roots = [1, 5, 25]
for n in n_roots:
    print(f"\nQuerying for {n} post-synaptic roots...")
    for i in range(n_trials):
        print(i)
        sample_roots = query_cell_info["pt_root_id"].sample(n).tolist()

        for spec_name, spec in output_specs.items():
            currtime = time.time()
            polars_synapses = synapse_query(spec_name, spec, post_ids=sample_roots)
            elapsed = time.time() - currtime
            rows.append(
                {
                    "n_roots": n,
                    "elapsed_seconds": elapsed,
                    "format": spec_name,
                    "partition_plan": True,
                    "extended_format": spec_name + "-with-partition-info",
                    "n_synapses": len(polars_synapses),
                }
            )
            if "range" in spec_name:
                currtime = time.time()
                polars_synapses = synapse_query(
                    spec_name, spec, post_ids=sample_roots, partition_plan=False
                )
                elapsed = time.time() - currtime
                rows.append(
                    {
                        "n_roots": n,
                        "elapsed_seconds": elapsed,
                        "format": spec_name,
                        "partition_plan": False,
                        "extended_format": spec_name + "-no-partition-info",
                        "n_synapses": len(polars_synapses),
                    }
                )
    print()
    print()
    # currtime = time.time()
    # materialization_synapses = client.materialize.synapse_query(
    #     post_ids=sample_roots,
    #     materialization_version=1412,
    # )
    # elapsed = time.time() - currtime
    # timing_rows.append(
    #     {"n_roots": n, "elapsed_seconds": elapsed, "format": "materialization"}
    # )


# print(materialization_synapses.shape[0])

# %%

import seaborn as sns

sns.stripplot(
    data=pd.DataFrame(rows).query("partition_plan == True"),
    x="n_roots",
    y="elapsed_seconds",
    hue="format",
    dodge=True,
    jitter=True,
)

# %%
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(5, 3))
sns.stripplot(
    data=pd.DataFrame(rows),
    x="n_roots",
    y="elapsed_seconds",
    hue="extended_format",
    dodge=True,
    jitter=True,
    ax=ax,
)
sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))


# %%
spec = output_specs["post_pt_root_id-4096"]

# %%
spec_name = "post_pt_root_id-1024-hash"
spec = output_specs[spec_name]
currtime = time.time()
polars_synapses = synapse_query(spec_name, spec, post_ids=sample_roots)
print(len(polars_synapses), "synapses found")
elapsed = time.time() - currtime

# %%
pl.Series(sample_roots).hash() % output_specs["post_pt_root_id-1024-hash"][
    "n_partitions"
]

# %%
slow_scan_synapses = (
    pl.scan_delta(base_out_path + f"/{spec_name}")
    .filter(pl.col("post_pt_root_id").is_in(sample_roots))
    .collect(engine="streaming")
)


# %%

import polars as pl

spec_name = "post_pt_root_id-1024"
dt = DeltaTable(base_out_path + f"/{spec_name}")

# Arrow table → Polars for easy manipulation
meta = pl.from_arrow(dt.get_add_actions(flatten=True))

# See what columns have stats
print(meta.columns)

# %%
# Find files where a column's max > some threshold
# (simulating what the engine does for pruning)
relevant = meta.filter(
    (pl.col("max.post_pt_root_id") >= 864691135730733497)
    & (pl.col("min.post_pt_root_id") <= 864691135730733497)
)
# print(relevant.select(["path", "min.my_column", "max.my_column", "num_records"]))
relevant

# %%

import matplotlib.pyplot as plt

# make a plot where y axis is partition id, x axis shows line from min to max post_pt_root_id from the metadata
meta = meta.with_columns(
    pl.col("partition.post_pt_root_id_partition").alias("partition_id"),
    pl.col("min.post_pt_root_id").alias("min_id"),
    pl.col("max.post_pt_root_id").alias("max_id"),
).filter((pl.col("min_id") > 1e15) & (pl.col("max_id") > 1e16))
plt.figure(figsize=(10, 20))
for row in meta.iter_rows(named=True):
    plt.plot(
        [row["min_id"], row["max_id"]],
        [row["partition_id"], row["partition_id"]],
        marker="o",
    )
plt.xlabel("post_pt_root_id range")
plt.ylabel("Partition ID")
plt.title("Partition ID vs post_pt_root_id range")
plt.grid()
plt.show()

# %%
meta.filter(pl.col("partition.post_pt_root_id_partition") == 886)

# %%
currtime = time.time()

query = (
    pl.scan_delta(base_out_path + f"/{spec_name}")
    .filter(pl.col("post_pt_root_id") == 864691135730733497)
    .collect(engine="streaming")
)

print(f"{time.time() - currtime:.3f} seconds elapsed.")
