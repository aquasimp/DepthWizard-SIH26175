"""Tests verifying textured GLB export, texture preservation on reload, and LODs."""

import numpy as np
import trimesh
from PIL import Image

from backend.depthwizard.mesh.export_glb import (
    export_all_lod_glbs,
    export_textured_glb_pygltflib,
)
from backend.depthwizard.mesh.heightmap_to_mesh import heightmap_to_mesh


def _extract_texture(loaded_scene_or_mesh):
    """Helper to extract non-null texture image from trimesh object."""
    if isinstance(loaded_scene_or_mesh, trimesh.Scene):
        for geom in loaded_scene_or_mesh.geometry.values():
            mat = getattr(geom.visual, "material", None)
            if mat is not None:
                tex = getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
                if tex is not None:
                    return tex
    elif hasattr(loaded_scene_or_mesh, "visual"):
        mat = getattr(loaded_scene_or_mesh.visual, "material", None)
        if mat is not None:
            return getattr(mat, "baseColorTexture", None) or getattr(mat, "image", None)
    return None


def test_glb_has_texture_all_three_lods(tmp_path):
    """Re-import each GLB with trimesh and assert material has non-null base-colour texture.

    Tests that terrain_lod0.glb, terrain_lod1.glb, and terrain_lod2.glb load without error
    and all contain a non-null base-colour texture of the expected size.
    """
    heightmap = np.random.uniform(50.0, 100.0, (256, 256)).astype(np.float32)
    # RGB image of size 512x512
    rgb_img = np.zeros((512, 512, 3), dtype=np.uint8)
    rgb_img[:, :, 0] = 200  # reddish
    rgb_img[:, :, 1] = 100  # greenish

    artifacts = export_all_lod_glbs(
        heightmap=heightmap,
        rgb_image=rgb_img,
        out_dir=tmp_path,
        gsd_m=0.33,
        z_exag=1.0,
    )

    expected_lods = ["lod0", "lod1", "lod2"]
    for lod_name in expected_lods:
        assert lod_name in artifacts, f"Missing {lod_name} in artifacts"
        glb_path = artifacts[lod_name]
        assert glb_path.exists(), f"GLB file does not exist: {glb_path}"

        # 1. Assert loads without error
        loaded = trimesh.load(str(glb_path), file_type="glb")
        assert loaded is not None

        # 2. Assert material has non-null base-colour texture image of expected size
        tex_img = _extract_texture(loaded)
        assert tex_img is not None, f"Material in {lod_name} has null baseColorTexture!"
        assert hasattr(tex_img, "size"), f"Texture in {lod_name} is not a valid image object"
        w, h = tex_img.size
        assert w == 512 and h == 512, f"Expected 512x512 texture, got {w}x{h}"


def test_export_textured_glb_pygltflib_fallback(tmp_path):
    """Directly test the pygltflib fallback exporter to guarantee robustness."""
    H = np.zeros((16, 16), dtype=np.float32)
    verts, faces, uvs = heightmap_to_mesh(H, gsd_m=1.0)
    pil_img = Image.new("RGB", (128, 128), color=(50, 150, 250))

    fallback_glb = tmp_path / "fallback.glb"
    export_textured_glb_pygltflib(
        vertices=verts,
        faces=faces,
        uvs=uvs,
        texture_image=pil_img,
        out_path=fallback_glb,
    )

    assert fallback_glb.exists()
    loaded = trimesh.load(str(fallback_glb), file_type="glb")
    tex_img = _extract_texture(loaded)

    assert tex_img is not None, "Fallback exporter failed to embed texture!"
    assert tex_img.size == (128, 128)
