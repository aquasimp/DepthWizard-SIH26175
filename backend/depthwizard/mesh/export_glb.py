"""GLB mesh export with embedded texture and fallback support."""

from pathlib import Path
from typing import Union

import numpy as np
import trimesh
from PIL import Image


def export_textured_glb(
    vertices: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray,
    texture_image: Image.Image,
    out_path: Union[str, Path],
) -> None:
    """Export textured 3D mesh as binary GLB file."""
    # Ensure texture is RGB
    if texture_image.mode != "RGB":
        texture_image = texture_image.convert("RGB")

    visual = trimesh.visual.TextureVisuals(
        uv=uvs,
        image=texture_image,
    )
    mesh = trimesh.Trimesh(
        vertices=vertices,
        faces=faces,
        visual=visual,
        process=False,
    )
    scene = trimesh.Scene(mesh)
    glb_bytes = scene.export(file_type="glb")
    with open(str(out_path), "wb") as f:
        f.write(glb_bytes)
