"""Tests for vectorized mesh generation, vertex/face counts, UVs, and ramp elevations."""

import numpy as np

from backend.depthwizard.mesh.decimate import generate_lod_meshes
from backend.depthwizard.mesh.heightmap_to_mesh import heightmap_to_mesh


def test_mesh_vertex_and_face_counts_formula():
    """Assert vertex and face counts match exact formulas: V = R*C, F = 2*(R-1)*(C-1)."""
    shapes = [(10, 15), (32, 32), (64, 128), (512, 512)]

    for R, C in shapes:
        H = np.zeros((R, C), dtype=np.float32)
        verts, faces, uvs = heightmap_to_mesh(H, gsd_m=0.33)

        expected_verts = R * C
        expected_faces = 2 * (R - 1) * (C - 1)

        assert len(verts) == expected_verts, f"Shape ({R},{C}): expected {expected_verts} verts, got {len(verts)}"
        assert len(faces) == expected_faces, f"Shape ({R},{C}): expected {expected_faces} faces, got {len(faces)}"
        assert len(uvs) == expected_verts


def test_uv_exact_boundaries():
    """Assert uv.min() == 0.0 and uv.max() == 1.0 EXACTLY."""
    H = np.zeros((64, 64), dtype=np.float32)
    _, _, uvs = heightmap_to_mesh(H)

    assert uvs.min() == 0.0, f"Expected uv.min() == 0.0, got {uvs.min()}"
    assert uvs.max() == 1.0, f"Expected uv.max() == 1.0, got {uvs.max()}"

    # Check corners
    u = uvs[:, 0].reshape(64, 64)
    v = uvs[:, 1].reshape(64, 64)

    assert u[0, 0] == 0.0 and v[0, 0] == 0.0
    assert u[0, -1] == 1.0 and v[0, -1] == 0.0
    assert u[-1, 0] == 0.0 and v[-1, 0] == 1.0
    assert u[-1, -1] == 1.0 and v[-1, -1] == 1.0


def test_synthetic_ramp_vertex_y_values():
    """Assert a synthetic ramp produces the expected vertex Y values with vertical exaggeration."""
    R, C = 50, 40
    # Linear ramp along rows: H[r, c] = 12.0 + 3.5 * r
    r_coords = np.arange(R, dtype=np.float32)[:, None]
    H = 12.0 + 3.5 * r_coords + np.zeros((R, C), dtype=np.float32)

    z_exag = 2.5
    verts, _, _ = heightmap_to_mesh(H, gsd_m=0.5, z_exag=z_exag)

    y_vals = verts[:, 1].reshape(R, C)
    expected_y = H * z_exag

    np.testing.assert_allclose(y_vals, expected_y, atol=1e-5)


def test_lod0_under_400k_vertices():
    """Assert LOD0 (512x512) has fewer than 400,000 vertices."""
    H = np.random.uniform(10.0, 50.0, (512, 512)).astype(np.float32)
    lods = generate_lod_meshes(H, gsd_m=0.33)

    verts_lod0, faces_lod0, _ = lods["lod0"]
    num_verts = len(verts_lod0)

    assert num_verts == 512 * 512  # 262,144
    assert num_verts < 400_000, f"LOD0 has {num_verts} vertices, exceeding 400k limit"
    assert len(faces_lod0) == 2 * 511 * 511  # 522,242
