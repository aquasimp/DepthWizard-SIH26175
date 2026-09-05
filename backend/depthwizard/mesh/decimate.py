"""Multi-resolution LOD generation using proper area-averaging decimation."""

from typing import Dict, Tuple

import cv2
import numpy as np

from depthwizard.mesh.heightmap_to_mesh import heightmap_to_mesh

LOD_RESOLUTIONS: Dict[str, Tuple[int, int]] = {
    "lod0": (512, 512),
    "lod1": (256, 256),
    "lod2": (128, 128),
}


def decimate_heightmap(
    heightmap: np.ndarray,
    target_shape: Tuple[int, int] = (512, 512),
) -> np.ndarray:
    """Downsample heightmap using INTER_AREA to prevent building-edge spiking artifacts.

    Args:
        heightmap: 2D numpy array of elevation values.
        target_shape: (height, width) target dimensions.

    Returns:
        Downsampled heightmap of shape target_shape as float32.
    """
    arr = np.asarray(heightmap, dtype=np.float32)
    h_tgt, w_tgt = target_shape
    if arr.shape == (h_tgt, w_tgt):
        return arr.copy()
    return cv2.resize(arr, (w_tgt, h_tgt), interpolation=cv2.INTER_AREA).astype(np.float32)


def generate_lod_meshes(
    heightmap: np.ndarray,
    gsd_m: float = 0.33,
    z_exag: float = 1.0,
) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Generate meshes for LOD0 (512x512), LOD1 (256x256), and LOD2 (128x128).

    Guarantees LOD0 vertex count is under 400k vertices (512x512 = 262,144 vertices).
    Maintains exact spatial extents across all LODs.

    Args:
        heightmap: Source elevation array.
        gsd_m: Ground sampling distance of the source grid.
        z_exag: Vertical elevation exaggeration.

    Returns:
        Dictionary mapping 'lod0', 'lod1', 'lod2' to (vertices, faces, uvs).
    """
    h_orig, w_orig = heightmap.shape[:2]
    # Physical extent in metres based on original grid
    extent_x = float(w_orig - 1) * float(gsd_m)
    extent_z = float(h_orig - 1) * float(gsd_m)

    lods: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}

    for lod_name, (h_tgt, w_tgt) in LOD_RESOLUTIONS.items():
        # Downsample elevation grid
        dec_h = decimate_heightmap(heightmap, (h_tgt, w_tgt))

        # Adjusted GSD so that all LODs share the exact same bounding box in 3D
        gsd_x = extent_x / float(w_tgt - 1) if w_tgt > 1 else gsd_m
        gsd_z = extent_z / float(h_tgt - 1) if h_tgt > 1 else gsd_m

        vertices, faces, uvs = heightmap_to_mesh(
            dec_h,
            gsd_m=gsd_m,
            z_exag=z_exag,
            gsd_x=gsd_x,
            gsd_z=gsd_z,
        )
        lods[lod_name] = (vertices, faces, uvs)

    return lods
