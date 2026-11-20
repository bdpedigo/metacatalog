# %%


import cloudvolume
import numpy as np
from caveclient import CAVEclient

client = CAVEclient("minnie65_phase3_v1")
client.info.get_datastack_info()
client.info.get_aligned_volume_info()
# %%
client.chunkedgraph.segmentation_info

# %%
cv: cloudvolume.frontends.graphene.CloudVolumeGraphene = (
    client.info.segmentation_cloudvolume()
)


# %%


def get_chunkedgraph_node_level(
    node_id: int, cv_graph: cloudvolume.frontends.graphene.CloudVolumeGraphene
) -> int:
    """Return the chunkedgraph level for a node id."""
    return int(cv_graph.meta.decode_layer_id(node_id))


def get_chunkedgraph_node_bounds(
    node_id: int,
    cv_graph: cloudvolume.frontends.graphene.CloudVolumeGraphene,
    pad_voxels: float = 0.0,
    pad_nm: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Return chunk indices and physical xyz bounds (min/max) for a node id.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        chunk_indices_xyz: shape (3,), integer chunk indices.
        physical_bounds_xyz: shape (2, 3), rows are [xyz_min, xyz_max].

    Notes
    -----
    For mesh containment checks, tiny boundary deviations can occur from quantization.
    Use pad_voxels (e.g. 0.5 or 1.0) to expand the physical bounds by that many
    watershed voxels in each direction.

    pad_nm can be used for isotropic physical padding in nm.
    """
    meta = cv_graph.meta
    level = int(meta.decode_layer_id(node_id))

    chunk_indices = np.asarray(meta.decode_chunk_position(node_id), dtype=np.int64)

    # L2 uses base graph chunk size; higher levels expand by fan_out^(level-2).
    base_chunk_size = np.asarray(meta.graph_chunk_size, dtype=np.int64)
    level_chunk_size = base_chunk_size * (int(meta.fan_out) ** max(0, level - 2))

    voxel_min = chunk_indices * level_chunk_size
    if meta.chunks_start_at_voxel_offset:
        voxel_min = voxel_min + np.asarray(
            meta.voxel_offset(meta.watershed_mip), dtype=np.int64
        )
    voxel_max = voxel_min + level_chunk_size

    resolution_nm = np.asarray(meta.resolution(meta.watershed_mip), dtype=np.float64)
    physical_min = voxel_min.astype(np.float64) * resolution_nm
    physical_max = voxel_max.astype(np.float64) * resolution_nm

    if pad_voxels != 0.0:
        pad_nm_vec = float(pad_voxels) * resolution_nm
        physical_min = physical_min - pad_nm_vec
        physical_max = physical_max + pad_nm_vec

    if pad_nm != 0.0:
        physical_min = physical_min - float(pad_nm)
        physical_max = physical_max + float(pad_nm)

    physical_bounds = np.vstack([physical_min, physical_max])

    return chunk_indices, physical_bounds


def get_dataset_bounds(
    cv_graph: cloudvolume.frontends.graphene.CloudVolumeGraphene,
) -> np.ndarray:
    """Return the global dataset physical bounds in nm.

    Returns
    -------
    np.ndarray
        Shape (2, 3), rows are [xyz_min, xyz_max] in nm.
    """
    meta = cv_graph.meta
    resolution_nm = np.asarray(meta.resolution(meta.watershed_mip), dtype=np.float64)
    voxel_offset = np.asarray(meta.voxel_offset(meta.watershed_mip), dtype=np.int64)
    volume_size = np.asarray(meta.volume_size(meta.watershed_mip), dtype=np.int64)

    dataset_min = voxel_offset.astype(np.float64) * resolution_nm
    dataset_max = (voxel_offset + volume_size).astype(np.float64) * resolution_nm

    return np.vstack([dataset_min, dataset_max])


def clip_bounds_to_dataset(
    bounds: np.ndarray,
    cv_graph: cloudvolume.frontends.graphene.CloudVolumeGraphene,
) -> np.ndarray:
    """Clip physical bounds to the global dataset extent.

    Parameters
    ----------
    bounds : np.ndarray
        Shape (2, 3), rows are [xyz_min, xyz_max] in nm.
    cv_graph : cloudvolume.frontends.graphene.CloudVolumeGraphene

    Returns
    -------
    np.ndarray
        Shape (2, 3), clipped bounds in nm.
    """
    dataset_bounds = get_dataset_bounds(cv_graph)

    return np.vstack(
        [
            np.maximum(bounds[0], dataset_bounds[0]),
            np.minimum(bounds[1], dataset_bounds[1]),
        ]
    )


def get_node_mesh_tolerance_nm(
    node_id: int,
    cv_graph: cloudvolume.frontends.graphene.CloudVolumeGraphene,
    use_half_grid: bool = True,
) -> float:
    """Return metadata-derived Draco tolerance in nm for this node's level.

    If mesh metadata is unavailable, returns 0.0.
    """
    meta = cv_graph.meta
    level = int(meta.decode_layer_id(node_id))
    try:
        draco_grid_size_nm = float(meta.get_draco_grid_size(level))
    except Exception:
        return 0.0

    if use_half_grid:
        return draco_grid_size_nm / 2.0
    return draco_grid_size_nm


# %%
# Extract global dataset bounds
dataset_bounds_nm = get_dataset_bounds(cv)
print("dataset_bounds [xyz_min, xyz_max] (nm):\n", dataset_bounds_nm)

import pyvista as pv

plotter = pv.Plotter()

# plotter.add_mesh(pv.make_tri_mesh(*mesh))

# add a bounding box for the chunk
box = pv.Box(bounds=dataset_bounds_nm.T.ravel())
plotter.add_mesh(box, style="wireframe", color="red")
plotter.show()


# %%
# Replace with any known valid node id for your dataset.
example_node_id = 864691135013856705

example_level = get_chunkedgraph_node_level(example_node_id, cv)
example_chunk_indices, example_physical_bounds = get_chunkedgraph_node_bounds(
    example_node_id, cv
)

print("node_id:", example_node_id)
print("level:", example_level)
print("chunk_indices (x, y, z):", example_chunk_indices)
print("physical_bounds shape:", example_physical_bounds.shape)
print("physical_bounds [xyz_min, xyz_max]:\n", example_physical_bounds)

# quick parity checks against existing CloudVolume helpers
assert example_level == cv.get_chunk_layer(example_node_id)
assert np.array_equal(
    example_chunk_indices,
    np.asarray(cv.meta.decode_chunk_position(example_node_id), dtype=np.int64),
)
assert example_physical_bounds.shape == (2, 3)


# %%

node_id = 458505144875965725  # level 6
node_id = 599823175373373452  # level 8
# node_id = 667658644764128064  # level 9
level = get_chunkedgraph_node_level(node_id, cv)
chunk_indices, physical_bounds = get_chunkedgraph_node_bounds(node_id, cv)

print("node_id:", node_id)
print("level:", level)
print("chunk_indices (x, y, z):", chunk_indices)
print("physical_bounds shape:", physical_bounds.shape)
print("physical_bounds [xyz_min, xyz_max]:\n", physical_bounds)

# %%
info = client.chunkedgraph.segmentation_info

# %%
mesh = cv.mesh.get(node_id)[node_id]
mesh = (mesh.vertices, mesh.faces)

# %%
print(mesh[0].min(axis=0), mesh[0].max(axis=0))

mesh_min = mesh[0].min(axis=0)
mesh_max = mesh[0].max(axis=0)

print("chunks_start_at_voxel_offset:", cv.meta.chunks_start_at_voxel_offset)
print(
    "mesh inside computed box:",
    np.all(mesh_min >= physical_bounds[0]) and np.all(mesh_max <= physical_bounds[1]),
)

mesh_tolerance_nm = get_node_mesh_tolerance_nm(node_id, cv, use_half_grid=True)
_, physical_bounds_tol = get_chunkedgraph_node_bounds(
    node_id, cv, pad_nm=mesh_tolerance_nm
)
print("mesh tolerance from metadata (nm):", mesh_tolerance_nm)
print(
    "mesh inside tolerance-padded box:",
    np.all(mesh_min >= physical_bounds_tol[0])
    and np.all(mesh_max <= physical_bounds_tol[1]),
)

# Offset diagnostics: compare with a zero-offset alternative.
level = get_chunkedgraph_node_level(node_id, cv)
chunk_indices = np.asarray(cv.meta.decode_chunk_position(node_id), dtype=np.int64)
base_chunk_size = np.asarray(cv.meta.graph_chunk_size, dtype=np.int64)
level_chunk_size = base_chunk_size * (int(cv.meta.fan_out) ** max(0, level - 2))
resolution_nm = np.asarray(cv.meta.resolution(cv.meta.watershed_mip), dtype=np.float64)

voxel_min_no_offset = chunk_indices * level_chunk_size
voxel_max_no_offset = voxel_min_no_offset + level_chunk_size
physical_no_offset = np.vstack(
    [
        voxel_min_no_offset.astype(np.float64) * resolution_nm,
        voxel_max_no_offset.astype(np.float64) * resolution_nm,
    ]
)
print(
    "mesh inside zero-offset box:",
    np.all(mesh_min >= physical_no_offset[0])
    and np.all(mesh_max <= physical_no_offset[1]),
)
# %%
# Clip computed chunk bounds to the global dataset bounds
clipped_bounds = clip_bounds_to_dataset(physical_bounds, cv)
print("clipped_bounds [xyz_min, xyz_max] (nm):\n", clipped_bounds)

# %%
import pyvista as pv

plotter = pv.Plotter()

plotter.add_mesh(pv.make_tri_mesh(*mesh))

# add a bounding box for the chunk
box = pv.Box(bounds=physical_bounds.T.ravel())
plotter.add_mesh(box, style="wireframe", color="red")
global_box = pv.Box(bounds=get_dataset_bounds(cv).T.ravel())
plotter.add_mesh(global_box, style="wireframe", color="blue")
clipped_box = pv.Box(bounds=clipped_bounds.T.ravel())
plotter.add_mesh(clipped_box, style="wireframe", color="green")
plotter.show()

# %%

# now, function to get bounds for all nodes at a given level, e.g. 8
# then, plot


def get_all_chunk_bounds_at_level(
    level: int,
    cv_graph: cloudvolume.frontends.graphene.CloudVolumeGraphene,
) -> np.ndarray:
    """Return physical bounds for all chunks at a given level.

    Returns
    -------
    np.ndarray
        Shape (N, 2, 3), where N is the number of chunks. Each entry has
        rows [xyz_min, xyz_max] in nm.
    """
    meta = cv_graph.meta
    base_chunk_size = np.asarray(meta.graph_chunk_size, dtype=np.int64)
    level_chunk_size = base_chunk_size * (int(meta.fan_out) ** max(0, level - 2))
    resolution_nm = np.asarray(meta.resolution(meta.watershed_mip), dtype=np.float64)
    voxel_offset = np.asarray(meta.voxel_offset(meta.watershed_mip), dtype=np.int64)
    volume_size = np.asarray(meta.volume_size(meta.watershed_mip), dtype=np.int64)

    # Number of chunks needed to cover the volume in each dimension
    n_chunks = np.ceil(volume_size / level_chunk_size).astype(np.int64)

    all_bounds = []
    for ix in range(n_chunks[0]):
        for iy in range(n_chunks[1]):
            for iz in range(n_chunks[2]):
                chunk_idx = np.array([ix, iy, iz], dtype=np.int64)
                voxel_min = chunk_idx * level_chunk_size
                if meta.chunks_start_at_voxel_offset:
                    voxel_min = voxel_min + voxel_offset
                voxel_max = voxel_min + level_chunk_size

                physical_min = voxel_min.astype(np.float64) * resolution_nm
                physical_max = voxel_max.astype(np.float64) * resolution_nm
                all_bounds.append([physical_min, physical_max])

    return np.array(all_bounds)


# %%
level_to_show = 8
all_bounds = get_all_chunk_bounds_at_level(level_to_show, cv)
print(f"Level {level_to_show}: {len(all_bounds)} chunks")

dataset_bounds_nm = get_dataset_bounds(cv)

import pyvista as pv

plotter = pv.Plotter()

# # Plot unclipped bounds in red
# for bounds in all_bounds:
#     box = pv.Box(bounds=bounds.T.ravel())
#     plotter.add_mesh(box, style="wireframe", color="red", opacity=0.3)

# Plot clipped bounds in green
for bounds in all_bounds:
    clipped = np.vstack(
        [
            np.maximum(bounds[0], dataset_bounds_nm[0]),
            np.minimum(bounds[1], dataset_bounds_nm[1]),
        ]
    )
    # Skip degenerate boxes (chunk entirely outside dataset)
    if np.all(clipped[1] > clipped[0]):
        box = pv.Box(bounds=clipped.T.ravel())
        plotter.add_mesh(box, style="wireframe", color="green", opacity=0.5)

# Global dataset bounds in blue
global_box = pv.Box(bounds=dataset_bounds_nm.T.ravel())
plotter.add_mesh(global_box, style="wireframe", color="blue", line_width=3)

plotter.show()

# %%
# Compute chunk bounds purely from the segmentation_info dict, no CloudVolume helpers.


def get_all_chunk_bounds_from_info(
    info: dict,
    level: int,
    fan_out: int = 2,
) -> np.ndarray:
    """Compute physical bounds (nm) for all chunks at a given level using only
    the raw segmentation_info dict.

    Parameters
    ----------
    info : dict
        The segmentation_info dict (from client.chunkedgraph.segmentation_info).
    level : int
        The chunkedgraph level to enumerate.
    fan_out : int
        Branching factor per dimension per level (always 2 for chunkedgraph).

    Returns
    -------
    np.ndarray
        Shape (N, 2, 3), rows are [xyz_min, xyz_max] in nm per chunk.
    """
    graph = info["graph"]
    base_chunk_size = np.asarray(graph["chunk_size"], dtype=np.int64)
    bounding_box_l2 = np.asarray(graph["bounding_box"], dtype=np.int64)
    cv_mip = int(graph["cv_mip"])

    # Find the scale entry matching cv_mip
    scale = info["scales"][cv_mip]
    resolution = np.asarray(scale["resolution"], dtype=np.float64)
    voxel_offset = np.asarray(scale["voxel_offset"], dtype=np.int64)

    chunks_start_at_voxel_offset = info.get("chunks_start_at_voxel_offset", False)

    # Level L chunk covers fan_out^(L-2) L2 chunks in each dimension
    scale_factor = fan_out ** max(0, level - 2)
    level_chunk_size = base_chunk_size * scale_factor

    # TODO: graph.bounding_box gives the full octree extent (power-of-2 padded),
    # which includes chunks outside the actual data volume. Need to reconcile
    # with the CV-based function which uses volume_size to only enumerate
    # chunks overlapping real data.
    n_chunks = np.ceil(bounding_box_l2 / scale_factor).astype(np.int64)

    all_bounds = []
    for ix in range(n_chunks[0]):
        for iy in range(n_chunks[1]):
            for iz in range(n_chunks[2]):
                chunk_idx = np.array([ix, iy, iz], dtype=np.int64)
                voxel_min = chunk_idx * level_chunk_size
                if chunks_start_at_voxel_offset:
                    voxel_min = voxel_min + voxel_offset
                voxel_max = voxel_min + level_chunk_size

                physical_min = voxel_min.astype(np.float64) * resolution
                physical_max = voxel_max.astype(np.float64) * resolution
                all_bounds.append([physical_min, physical_max])

    return np.array(all_bounds)


# %%
info = client.chunkedgraph.segmentation_info
level_to_show = 8
all_bounds_from_info = get_all_chunk_bounds_from_info(info, level_to_show)
print(f"Level {level_to_show} from info dict: {len(all_bounds_from_info)} chunks")
print(
    f"  n_chunks per dim: {np.ceil(np.asarray(info['graph']['bounding_box']) / (2 ** (level_to_show - 2))).astype(int)}"
)
print(
    f"  level chunk size (voxels): {np.asarray(info['graph']['chunk_size']) * 2 ** (level_to_show - 2)}"
)

scale = info["scales"][info["graph"]["cv_mip"]]
resolution = np.asarray(scale["resolution"], dtype=np.float64)
voxel_offset = np.asarray(scale["voxel_offset"], dtype=np.int64)
volume_size = np.asarray(scale["size"], dtype=np.int64)
dataset_min = voxel_offset.astype(np.float64) * resolution
dataset_max = (voxel_offset + volume_size).astype(np.float64) * resolution
print(f"  dataset bounds (nm): min={dataset_min}, max={dataset_max}")
print(f"  dataset size (nm): {dataset_max - dataset_min}")

# %%
import pyvista as pv

dataset_bounds_info = np.vstack([dataset_min, dataset_max])

plotter = pv.Plotter()

# Plot all chunk bounds from info in red
for bounds in all_bounds_from_info:
    box = pv.Box(bounds=bounds.T.ravel())
    plotter.add_mesh(box, style="wireframe", color="red", opacity=0.3)

# Global dataset bounds in blue
global_box = pv.Box(bounds=dataset_bounds_info.T.ravel())
plotter.add_mesh(global_box, style="wireframe", color="blue", line_width=3)

plotter.show()


# %%
# Verify matches the CloudVolume-based function
all_bounds_from_cv = get_all_chunk_bounds_at_level(level_to_show, cv)
assert np.allclose(all_bounds_from_info, all_bounds_from_cv), "Mismatch!"
print("  Matches CloudVolume-based computation: OK")
