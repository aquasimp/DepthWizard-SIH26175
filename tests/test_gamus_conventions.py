"""Unit tests verifying GAMUS dataset conventions against official benchmark standards.

Asserts:
1. Pairing rule: stripping last 6 characters from RGB filename and appending AGL.h5 / CLS.h5.
2. HDF5 dataset key: 'image' used consistently across RGB, AGL, and CLS files.
3. Dtypes: RGB (uint8), AGL (float32), CLS (integer-valued).
4. Class values: all class IDs must fall strictly within the official set {0..6}.
"""

from pathlib import Path
import h5py
import numpy as np
import pytest

SAMPLE_DIR = Path("artifacts/v1.1.0/sample_triplet")
SAMPLE_RGB = SAMPLE_DIR / "images/train/DC_01_25_RGB.h5"
SAMPLE_AGL = SAMPLE_DIR / "heights/train/DC_01_25_AGL.h5"
SAMPLE_CLS = SAMPLE_DIR / "classes/train/DC_01_25_CLS.h5"


def test_gamus_filename_pairing_rule() -> None:
    """Verify official pairing rule: base = filename[:-6], then base + CLS.h5 / AGL.h5."""
    test_cases = [
        ("DC_01_25_RGB.h5", "DC_01_25_AGL.h5", "DC_01_25_CLS.h5"),
        ("NYC_04_12_RGB.h5", "NYC_04_12_AGL.h5", "NYC_04_12_CLS.h5"),
        ("PHL_10_05_RGB.h5", "PHL_10_05_AGL.h5", "PHL_10_05_CLS.h5"),
    ]
    for rgb_name, expected_agl, expected_cls in test_cases:
        base_name = rgb_name[:-6]
        agl_name = f"{base_name}AGL.h5"
        cls_name = f"{base_name}CLS.h5"
        assert agl_name == expected_agl, f"Pairing mismatch for AGL: {agl_name} != {expected_agl}"
        assert cls_name == expected_cls, f"Pairing mismatch for CLS: {cls_name} != {expected_cls}"


def test_gamus_hdf5_keys() -> None:
    """Verify that all three GAMUS HDF5 modalities use the dataset key 'image'."""
    assert SAMPLE_RGB.exists(), f"Sample RGB file missing at {SAMPLE_RGB}"
    assert SAMPLE_AGL.exists(), f"Sample AGL file missing at {SAMPLE_AGL}"
    assert SAMPLE_CLS.exists(), f"Sample CLS file missing at {SAMPLE_CLS}"

    with h5py.File(SAMPLE_RGB, "r") as f_rgb:
        assert "image" in f_rgb, "RGB HDF5 missing 'image' key"
        assert f_rgb["image"].shape == (1024, 1024, 3)

    with h5py.File(SAMPLE_AGL, "r") as f_agl:
        assert "image" in f_agl, "AGL HDF5 missing 'image' key"
        assert f_agl["image"].shape == (1024, 1024)

    with h5py.File(SAMPLE_CLS, "r") as f_cls:
        assert "image" in f_cls, "CLS HDF5 missing 'image' key"
        assert f_cls["image"].shape == (1024, 1024)


def test_gamus_dtypes() -> None:
    """Verify dtypes: RGB is uint8, AGL is float32, CLS is convertible to integer."""
    with h5py.File(SAMPLE_RGB, "r") as f_rgb:
        rgb = f_rgb["image"][()]
        assert rgb.dtype == np.uint8, f"Expected RGB uint8, got {rgb.dtype}"

    with h5py.File(SAMPLE_AGL, "r") as f_agl:
        agl = f_agl["image"][()]
        assert agl.dtype == np.float32, f"Expected AGL float32, got {agl.dtype}"

    with h5py.File(SAMPLE_CLS, "r") as f_cls:
        cls_arr = f_cls["image"][()]
        # May be stored as float32 or int in HDF5, but all values must be exact integers
        assert np.all(cls_arr == np.floor(cls_arr)), "CLS contains non-integer values"


def test_gamus_class_values_in_official_set() -> None:
    """Verify that semantic classes strictly conform to the 7 official GAMUS classes:
    0: others/background (ignore)
    1: ground
    2: low vegetation
    3: buildings
    4: water
    5: road
    6: tree
    """
    with h5py.File(SAMPLE_CLS, "r") as f_cls:
        cls_arr = f_cls["image"][()].astype(np.int64)
        unique_classes = set(np.unique(cls_arr))
        official_classes = {0, 1, 2, 3, 4, 5, 6}
        unexpected = unique_classes - official_classes
        assert len(unexpected) == 0, f"Unexpected class IDs found in CLS raster: {unexpected}"
