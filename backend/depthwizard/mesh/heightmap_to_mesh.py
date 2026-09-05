"""Vectorized numpy grid triangulation for heightmaps."""

from typing import Tuple

import numpy as np


def heightmap_to_mesh(
    heightmap: np.ndarray,
    gsd_m: float = 0.33,
    z_exag: float = 1.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert an RxC heightmap to (vertices, faces, uvs) using vectorized triangulation.

    Vertices are in Y-UP right-handed frame: (x, y, z) = (c * gsd, H[r, c] * z_exag, r * gsd).
    UV coordinates map identity: u = c / (C - 1), v = r / (R - 1).
    """
    R, C = heightmap.shape
    r_idx, c_idx = np.meshgrid(np.arange(R), np.arange(C), indexing="ij")

    # Vertices
    x = (c_idx * gsd_m).astype(np.float32)
    y = (heightmap * z_exag).astype(np.float32)
    z = (r_idx * gsd_m).astype(np.float32)
    vertices = np.stack([x, y, z], axis=-1).reshape(-1, 3)

    # UVs
    u = (c_idx / (C - 1)).astype(np.float32)
    v = (r_idx / (R - 1)).astype(np.float32)
    uvs = np.stack([u, v], axis=-1).reshape(-1, 2)

    # Faces (two triangles per quad)
    v_idx = np.arange(R * C, dtype=np.int32).reshape(R, C)
    tl = v_idx[:-1, :-1].reshape(-1)
    tr = v_idx[:-1, 1:].reshape(-1)
    bl = v_idx[1:, :-1].reshape(-1)
    br = v_idx[1:, 1:].reshape(-1)

    tri1 = np.stack([tl, bl, tr], axis=-1)
    tri2 = np.stack([tr, bl, br], axis=-1)
    faces = np.vstack([tri1, tri2])

    return vertices, faces, uvs
