# %%

import numpy as np
import polars as pl
from cloudpathlib import CloudPath
from deltalake import DeltaTable

base_path = CloudPath(
    "gs://mat_dbs/public/deltalake_exports/minnie65_phase3_v1/v1507/synapses_pni_2"
)

partitions = ["ctr_pt_position_morton", "id", "post_pt_root_id", "pre_pt_root_id"]

# %%

results = []

for partition in partitions:
    table_path = str(base_path / partition)
    print(f"\n{'=' * 60}")
    print(f"Partition scheme: {partition}")
    print(f"Path: {table_path}")
    print(f"{'=' * 60}")

    try:
        dt = DeltaTable(table_path)
        actions = pl.from_arrow(dt.get_add_actions())

        sizes = actions["size_bytes"].to_numpy()
        num_files = len(sizes)
        total_size = sizes.sum()
        mean_size = sizes.mean()
        median_size = np.median(sizes)
        std_size = sizes.std()
        min_size = sizes.min()
        max_size = sizes.max()
        cv = std_size / mean_size if mean_size > 0 else float("nan")
        ratio_max_min = max_size / min_size if min_size > 0 else float("nan")

        print(f"  Number of files: {num_files}")
        print(f"  Total size: {total_size / 1e9:.2f} GB")
        print(f"  Mean file size: {mean_size / 1e6:.2f} MB")
        print(f"  Median file size: {median_size / 1e6:.2f} MB")
        print(f"  Std file size: {std_size / 1e6:.2f} MB")
        print(f"  Min file size: {min_size / 1e6:.2f} MB")
        print(f"  Max file size: {max_size / 1e6:.2f} MB")
        print(f"  Coefficient of variation: {cv:.4f}")
        print(f"  Max/Min ratio: {ratio_max_min:.2f}")

        # Percentile distribution
        percentiles = [5, 25, 50, 75, 95]
        pct_values = np.percentile(sizes, percentiles)
        print("  Percentiles (MB):")
        for p, v in zip(percentiles, pct_values):
            print(f"    P{p}: {v / 1e6:.2f}")

        results.append(
            {
                "partition": partition,
                "num_files": num_files,
                "total_size_gb": total_size / 1e9,
                "mean_size_mb": mean_size / 1e6,
                "median_size_mb": median_size / 1e6,
                "std_size_mb": std_size / 1e6,
                "cv": cv,
                "max_min_ratio": ratio_max_min,
            }
        )

    except Exception as e:
        print(f"  ERROR: {e}")
        results.append({"partition": partition, "error": str(e)})

# %%

table_path = (
    "gs://allen-minnie-phase3/mat_deltalakes/v1412/synapses_pni_2_v1412_deltalake"
)
dt = DeltaTable(table_path)
actions = pl.from_arrow(dt.get_add_actions())


# %%

# Summary comparison
print("\n\nSummary Comparison")
print("=" * 80)
summary_df = pl.DataFrame(results)
print(summary_df)


# %%

synapses = pl.scan_delta(str(base_path / "ctr_pt_position_morton"))

synapses = synapses.with_columns(
    pl.col("ctr_pt_position_x") * 4,  # convert from voxels to nanometers
    pl.col("ctr_pt_position_y") * 4,
    pl.col("ctr_pt_position_z") * 40,
)

synapses.collect_schema()


# %%

import time

currtime = time.time()
bounds = synapses.select(
    pl.col("^ctr_pt_position_[xyz]$").min().name.suffix("_min"),
    pl.col("^ctr_pt_position_[xyz]$").max().name.suffix("_max"),
).collect(engine="streaming")
print(f"{time.time() - currtime:.3f} seconds elapsed.")


bounds

# %%

# sample a point uniformly at random from the bounding box

pos = np.random.uniform(
    low=[
        bounds["ctr_pt_position_x_min"][0],
        bounds["ctr_pt_position_y_min"][0],
        bounds["ctr_pt_position_z_min"][0],
    ],
    high=[
        bounds["ctr_pt_position_x_max"][0],
        bounds["ctr_pt_position_y_max"][0],
        bounds["ctr_pt_position_z_max"][0],
    ],
)
# midpoint
pos = [
    (bounds["ctr_pt_position_x_min"][0] + bounds["ctr_pt_position_x_max"][0]) / 2,
    (bounds["ctr_pt_position_y_min"][0] + bounds["ctr_pt_position_y_max"][0]) / 2,
    (bounds["ctr_pt_position_z_min"][0] + bounds["ctr_pt_position_z_max"][0]) / 2,
]

radius = 5000  # 10 microns

bbox = (
    (pl.col("ctr_pt_position_x") >= pos[0] - radius)
    & (pl.col("ctr_pt_position_x") <= pos[0] + radius)
    & (pl.col("ctr_pt_position_y") >= pos[1] - radius)
    & (pl.col("ctr_pt_position_y") <= pos[1] + radius)
    & (pl.col("ctr_pt_position_z") >= pos[2] - radius)
    & (pl.col("ctr_pt_position_z") <= pos[2] + radius)
)


currtime = time.time()
query_synapses = synapses.filter(bbox).collect(engine="streaming")
print(f"{time.time() - currtime:.3f} seconds elapsed.")
print(f"Number of synapses within {radius} nm of random point: {len(query_synapses)}")

# %%
dt = DeltaTable(str(base_path / "ctr_pt_position_morton"))
actions = pl.from_arrow(dt.get_add_actions(flatten=True))

# The flattened actions include min/max stats per file
# Check which files overlap with the bbox
touched = actions.filter(
    (pl.col("min.ctr_pt_position_x") * 4 <= pos[0] + radius)
    & (pl.col("max.ctr_pt_position_x") * 4 >= pos[0] - radius)
    & (pl.col("min.ctr_pt_position_y") * 4 <= pos[1] + radius)
    & (pl.col("max.ctr_pt_position_y") * 4 >= pos[1] - radius)
    & (pl.col("min.ctr_pt_position_z") * 40 <= pos[2] + radius)
    & (pl.col("max.ctr_pt_position_z") * 40 >= pos[2] - radius)
)

print(f"Files touched: {len(touched)} / {len(actions)}")
print(
    f"Data scanned: {touched['size_bytes'].sum() / 1e6:.1f} MB / {actions['size_bytes'].sum() / 1e6:.1f} MB"
)

# %%
from caveclient import CAVEclient

client = CAVEclient("minnie65_phase3_v1", version=1507)

# %%
currtime = time.time()

back = client.materialize.query_table(
    "synapses_pni_2",
    filter_spatial_dict={
        "ctr_pt_position": [
            [
                pos[0] / 4 - radius / 4,
                pos[1] / 4 - radius / 4,
                pos[2] / 40 - radius / 40,
            ],
            [
                pos[0] / 4 + radius / 4,
                pos[1] / 4 + radius / 4,
                pos[2] / 40 + radius / 40,
            ],
        ]
    },
)
print(f"{time.time() - currtime:.3f} seconds elapsed.")

# %%
from caveclient import CAVEclient

client = CAVEclient("minnie65_phase3_v1", version=1507)


cells = client.materialize.query_view("aibs_cell_info")

sample_roots = cells["pt_root_id"].sample(25).to_list()

# %%
import time

currtime = time.time()
cave_result = client.materialize.query_table(
    "synapses_pni_2",
    filter_in_dict={"post_pt_root_id": sample_roots},
)
print(f"{time.time() - currtime:.3f} seconds elapsed.")

# %%

synapses_by_post = pl.scan_delta(str(base_path / "post_pt_root_id")).filter(
    pl.col("post_pt_root_id").is_in(sample_roots)
)

currtime = time.time()
delta_result = synapses_by_post.collect(engine="streaming")
print(f"{time.time() - currtime:.3f} seconds elapsed.")

# %%

# use delta table to extract the partitions that are relevant to the query, then use polars to read just those partitions with a filter pushdown
dt = DeltaTable(str(base_path / "post_pt_root_id"))
actions = pl.from_arrow(dt.get_add_actions(flatten=True))
# The flattened actions include min/max stats per file
# Check which files overlap with the filter values

touched_partitions = []
for sample_root in sample_roots:
    touched = actions.filter(
        (pl.col("min.post_pt_root_id") <= sample_root)
        & (pl.col("max.post_pt_root_id") >= sample_root)
    )
    touched_partitions.extend(touched["partition.post_pt_root_id_partition"].to_list())

# %%

table = pl.scan_delta(
    "gs://allen-minnie-phase3/mat_deltalakes/v1412/synapses_pni_2_v1412_deltalake"
).filter(pl.col("post_pt_root_id").is_in(sample_roots))

post_list = [sample_roots] if isinstance(sample_roots, (int,)) else list(sample_roots)
partition_list = [root_id % 1024 for root_id in post_list]
join_index = pl.DataFrame(
    {"post_pt_root_id": post_list, "post_pt_root_id_partition": partition_list}
).lazy()
# this looks janky, but having this filter here really helps performance
# polars is not natively pushing down the implicit filter that is in
# the join
table = table.filter(
    pl.col("post_pt_root_id").is_in(post_list),
    pl.col("post_pt_root_id_partition").is_in(partition_list),
)
table = table.join(
    join_index, on=["post_pt_root_id", "post_pt_root_id_partition"], how="semi"
)

currtime = time.time()
original_result = table.collect(engine="streaming")
print(f"{time.time() - currtime:.3f} seconds elapsed.")
