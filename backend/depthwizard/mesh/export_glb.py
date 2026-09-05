"""GLB mesh export with embedded texture and robust pygltflib fallback."""

import io
from pathlib import Path
from typing import Dict, Union

import numpy as np
import pygltflib
import trimesh
from PIL import Image

from depthwizard.mesh.decimate import generate_lod_meshes
from depthwizard.mesh.texture import prepare_texture


def export_textured_glb_pygltflib(
    vertices: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray,
    texture_image: Image.Image,
    out_path: Union[str, Path],
) -> Path:
    """Fallback GLB exporter using pygltflib to guarantee texture embedding.

    Addresses mikedh/trimesh issue #1296 where texture visuals may be silently dropped.
    """
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    img_buf = io.BytesIO()
    texture_image.convert("RGB").save(img_buf, format="JPEG", quality=90)
    img_bytes = img_buf.getvalue()

    v_bytes = vertices.astype(np.float32).tobytes()
    uv_bytes = uvs.astype(np.float32).tobytes()
    f_bytes = faces.astype(np.uint32).tobytes()

    def pad4(b: bytes) -> bytes:
        rem = len(b) % 4
        return b + (b"\x00" * (4 - rem)) if rem != 0 else b

    v_padded = pad4(v_bytes)
    uv_padded = pad4(uv_bytes)
    f_padded = pad4(f_bytes)
    img_padded = pad4(img_bytes)

    blob = v_padded + uv_padded + f_padded + img_padded

    offset_v = 0
    len_v = len(v_bytes)

    offset_uv = len(v_padded)
    len_uv = len(uv_bytes)

    offset_f = offset_uv + len(uv_padded)
    len_f = len(f_bytes)

    offset_img = offset_f + len(f_padded)
    len_img = len(img_bytes)

    gltf = pygltflib.GLTF2(
        scene=0,
        scenes=[pygltflib.Scene(nodes=[0])],
        nodes=[pygltflib.Node(mesh=0)],
        meshes=[
            pygltflib.Mesh(
                primitives=[
                    pygltflib.Primitive(
                        attributes=pygltflib.Attributes(POSITION=0, TEXCOORD_0=1),
                        indices=2,
                        material=0,
                    )
                ]
            )
        ],
        materials=[
            pygltflib.Material(
                pbrMetallicRoughness=pygltflib.PbrMetallicRoughness(
                    baseColorTexture=pygltflib.TextureInfo(index=0),
                    metallicFactor=0.0,
                    roughnessFactor=1.0,
                )
            )
        ],
        textures=[pygltflib.Texture(source=0, sampler=0)],
        samplers=[pygltflib.Sampler(magFilter=pygltflib.LINEAR, minFilter=pygltflib.LINEAR)],
        images=[pygltflib.Image(bufferView=3, mimeType="image/jpeg")],
        buffers=[pygltflib.Buffer(byteLength=len(blob))],
        bufferViews=[
            pygltflib.BufferView(
                buffer=0, byteOffset=offset_v, byteLength=len_v, target=pygltflib.ARRAY_BUFFER
            ),
            pygltflib.BufferView(
                buffer=0, byteOffset=offset_uv, byteLength=len_uv, target=pygltflib.ARRAY_BUFFER
            ),
            pygltflib.BufferView(
                buffer=0,
                byteOffset=offset_f,
                byteLength=len_f,
                target=pygltflib.ELEMENT_ARRAY_BUFFER,
            ),
            pygltflib.BufferView(buffer=0, byteOffset=offset_img, byteLength=len_img),
        ],
        accessors=[
            pygltflib.Accessor(
                bufferView=0,
                byteOffset=0,
                componentType=pygltflib.FLOAT,
                count=len(vertices),
                type=pygltflib.VEC3,
                max=vertices.max(axis=0).tolist(),
                min=vertices.min(axis=0).tolist(),
            ),
            pygltflib.Accessor(
                bufferView=1,
                byteOffset=0,
                componentType=pygltflib.FLOAT,
                count=len(uvs),
                type=pygltflib.VEC2,
                max=uvs.max(axis=0).tolist(),
                min=uvs.min(axis=0).tolist(),
            ),
            pygltflib.Accessor(
                bufferView=2,
                byteOffset=0,
                componentType=pygltflib.UNSIGNED_INT,
                count=faces.size,
                type=pygltflib.SCALAR,
                max=[int(faces.max())],
                min=[int(faces.min())],
            ),
        ],
    )
    gltf.set_binary_blob(blob)
    glb_bytes = b"".join(gltf.save_to_bytes())

    with open(out_file, "wb") as f:
        f.write(glb_bytes)

    return out_file


def export_textured_glb(
    vertices: np.ndarray,
    faces: np.ndarray,
    uvs: np.ndarray,
    texture_image: Union[Image.Image, np.ndarray, Path, str],
    out_path: Union[str, Path],
) -> Path:
    """Export textured 3D mesh as binary GLB file.

    Tries primary trimesh export with automatic pygltflib fallback if
    texture is dropped or fails to export.

    Args:
        vertices: (V, 3) vertex coordinates in Y-UP frame.
        faces: (F, 3) triangle indices.
        uvs: (V, 2) texture coordinates in [0.0, 1.0].
        texture_image: PIL Image or numpy array or path to texture image.
        out_path: Target path for .glb file.

    Returns:
        Path to the saved GLB file.
    """
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Prepare PIL image
    if isinstance(texture_image, (str, Path)):
        pil_img = Image.open(str(texture_image)).convert("RGB")
    elif isinstance(texture_image, np.ndarray):
        pil_img = Image.fromarray(texture_image).convert("RGB")
    elif isinstance(texture_image, Image.Image):
        pil_img = texture_image.convert("RGB")
    else:
        raise TypeError(f"Unsupported texture image type: {type(texture_image)}")

    # 1. Primary path: trimesh export
    success = False
    try:
        visual = trimesh.visual.TextureVisuals(
            uv=uvs,
            image=pil_img,
        )
        mesh = trimesh.Trimesh(
            vertices=vertices,
            faces=faces,
            visual=visual,
            process=False,
        )
        scene = trimesh.Scene(mesh)
        glb_bytes = scene.export(file_type="glb")

        # Verify that the exported bytes contain valid texture upon reload
        loaded = trimesh.load(io.BytesIO(glb_bytes), file_type="glb")
        if isinstance(loaded, trimesh.Scene):
            for geom in loaded.geometry.values():
                mat = getattr(geom.visual, "material", None)
                if mat and (
                    getattr(mat, "baseColorTexture", None) is not None
                    or getattr(mat, "image", None) is not None
                ):
                    success = True
                    break
        elif hasattr(loaded, "visual"):
            mat = getattr(loaded.visual, "material", None)
            if mat and (
                getattr(mat, "baseColorTexture", None) is not None
                or getattr(mat, "image", None) is not None
            ):
                success = True

        if success:
            with open(out_file, "wb") as f:
                f.write(glb_bytes)
            return out_file
    except Exception:
        success = False

    # 2. Fallback path: pygltflib export
    return export_textured_glb_pygltflib(
        vertices=vertices,
        faces=faces,
        uvs=uvs,
        texture_image=pil_img,
        out_path=out_file,
    )


def export_all_lod_glbs(
    heightmap: np.ndarray,
    rgb_image: np.ndarray,
    out_dir: Union[str, Path],
    gsd_m: float = 0.33,
    z_exag: float = 1.0,
) -> Dict[str, Path]:
    """Generate and export all 3 LOD GLBs (lod0, lod1, lod2) and texture.jpg.

    LOD0: 512x512 (<400k vertices)
    LOD1: 256x256
    LOD2: 128x128

    Args:
        heightmap: Source elevation array.
        rgb_image: Source RGB imagery array (H, W, 3).
        out_dir: Destination directory.
        gsd_m: Ground sampling distance.
        z_exag: Vertical elevation exaggeration.

    Returns:
        Dictionary mapping 'lod0', 'lod1', 'lod2', and 'texture' to file paths.
    """
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Prepare texture
    tex_path = dest / "texture.jpg"
    prepare_texture(rgb_image, tex_path, max_dim=4096, quality=90)
    tex_img = Image.open(str(tex_path)).convert("RGB")

    # 2. Generate multi-resolution LOD meshes
    lod_meshes = generate_lod_meshes(heightmap, gsd_m=gsd_m, z_exag=z_exag)

    artifacts: Dict[str, Path] = {"texture": tex_path}

    for lod_name, (verts, faces, uvs) in lod_meshes.items():
        glb_path = dest / f"terrain_{lod_name}.glb"
        export_textured_glb(
            vertices=verts,
            faces=faces,
            uvs=uvs,
            texture_image=tex_img,
            out_path=glb_path,
        )
        artifacts[lod_name] = glb_path

    return artifacts
