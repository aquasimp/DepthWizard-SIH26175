"""Vectorized numpy grid triangulation for heightmaps."""

from typing import Tuple

import numpy as np


def heightmap_to_mesh(
    heightmap: np.ndarray,
    gsd_m: float = 0.33,
    z_exag: float = 0.2,
    gsd_x: float = 0.0,
    gsd_z: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert an RxC heightmap to (vertices, faces, uvs) using vectorized triangulation.

    Emits vertices in a Y-UP right-handed frame (Three.js convention):
      x = c * gsd_x
      y = H[r, c] * z_exag
      z = r * gsd_z
    Face winding is counter-clockwise (CCW) when viewed from +Y (up).
    UV coordinates map the identity:
      u = c / (C - 1)
      v = r / (R - 1)

    Args:
        heightmap: 2D numpy array of elevations with shape (R, C).
        gsd_m: Ground sampling distance in metres (used if gsd_x or gsd_z is 0).
        z_exag: Vertical elevation exaggeration factor.
        gsd_x: Specific horizontal sampling distance (optional).
        gsd_z: Specific vertical/depth sampling distance (optional).

    Returns:
        Tuple of (vertices (V, 3), faces (F, 3), uvs (V, 2))
    """
    arr = np.asarray(heightmap, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    elif arr.ndim != 2:
        raise ValueError(f"Expected 2D heightmap array, got shape {arr.shape}")

    R, C = arr.shape
    if R < 2 or C < 2:
        raise ValueError(f"Heightmap must be at least 2x2, got {R}x{C}")

    spacing_x = float(gsd_x) if gsd_x > 0.0 else float(gsd_m)
    spacing_z = float(gsd_z) if gsd_z > 0.0 else float(gsd_m)

    # 1. Coordinate grids
    r_idx, c_idx = np.meshgrid(np.arange(R), np.arange(C), indexing="ij")

    # 2. Vertices: (x, y, z) in Y-UP right-handed frame
    x = (c_idx.astype(np.float32) * spacing_x)
    y = (arr * float(z_exag)).astype(np.float32)
    z = (r_idx.astype(np.float32) * spacing_z)
    vertices = np.stack([x, y, z], axis=-1).reshape(-1, 3)

    # 3. UVs: exact identity map [0.0, 1.0]
    u = (c_idx.astype(np.float32) / float(C - 1))
    v = (r_idx.astype(np.float32) / float(R - 1))
    uvs = np.stack([u, v], axis=-1).reshape(-1, 2)

    # 4. Faces (two triangles per quad, counter-clockwise winding from +Y)
    v_idx = np.arange(R * C, dtype=np.int32).reshape(R, C)
    tl = v_idx[:-1, :-1].reshape(-1)
    tr = v_idx[:-1, 1:].reshape(-1)
    bl = v_idx[1:, :-1].reshape(-1)
    br = v_idx[1:, 1:].reshape(-1)

    # Quad = [tl, tr, br, bl]
    # Triangle 1: (tl, bl, tr) -> normal points +Y
    # Triangle 2: (tr, bl, br) -> normal points +Y
    tri1 = np.stack([tl, bl, tr], axis=-1)
    tri2 = np.stack([tr, bl, br], axis=-1)
    faces = np.vstack([tri1, tri2])

    return vertices, faces, uvs
