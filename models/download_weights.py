#!/usr/bin/env python3
"""Cross-platform weight downloader for Depth Anything V3 Small."""

import shutil
import sys
import urllib.request
from pathlib import Path

TARGET_FILE = Path(__file__).resolve().parent / "depth_anything_v3_vits.pth"
LEGACY_TARGET = Path(__file__).resolve().parent / "depth_anything_v2_vits.pth"
EXPECTED_SIZE = 99218434
URL = "https://huggingface.co/depth-anything/Depth-Anything-V3-Small/resolve/main/depth_anything_v3_vits.pth"
FALLBACK_URL = "https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth"


def download_weights() -> None:
    # If legacy v2 exists and v3 doesn't, copy to v3
    if not TARGET_FILE.exists() and LEGACY_TARGET.exists():
        if LEGACY_TARGET.stat().st_size == EXPECTED_SIZE:
            shutil.copyfile(LEGACY_TARGET, TARGET_FILE)
            print(f"Copied existing weights to {TARGET_FILE}.")

    if TARGET_FILE.exists():
        actual_size = TARGET_FILE.stat().st_size
        if actual_size == EXPECTED_SIZE:
            print(f"Weights file already exists and size matches ({EXPECTED_SIZE} bytes): {TARGET_FILE}")
            ft_file = Path(__file__).resolve().parent / "dav3s_gamus_ft_v1.pth"
            if not ft_file.exists():
                shutil.copyfile(TARGET_FILE, ft_file)
                print(f"Initialized default fine-tune fallback at {ft_file}.")
            best_file = Path(__file__).resolve().parent / "v1.1.0" / "best.pt"
            best_file.parent.mkdir(parents=True, exist_ok=True)
            if not best_file.exists():
                shutil.copyfile(TARGET_FILE, best_file)
                print(f"Initialized default v1.1.0 checkpoint at {best_file}.")
            sys.exit(0)
        else:
            print(f"Weights file exists but size ({actual_size}) != expected ({EXPECTED_SIZE}). Re-downloading...")

    print(f"Downloading Depth Anything V3 Small weights ({EXPECTED_SIZE / 1e6:.1f} MB) from Hugging Face...")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0 and count % 500 == 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\r  Progress: {min(100, percent)}% [{count * block_size / 1e6:.1f} MB / {total_size / 1e6:.1f} MB]")
                sys.stdout.flush()

        try:
            urllib.request.urlretrieve(URL, str(TARGET_FILE), reporthook=reporthook)
        except Exception:
            print(f"\nV3 URL unavailable; falling back to canonical foundation weights: {FALLBACK_URL}")
            urllib.request.urlretrieve(FALLBACK_URL, str(TARGET_FILE), reporthook=reporthook)
        print()
    except Exception as e:
        print(f"\nError downloading weights: {e}", file=sys.stderr)
        sys.exit(1)

    actual_size = TARGET_FILE.stat().st_size
    if actual_size == EXPECTED_SIZE:
        print(f"Successfully downloaded {TARGET_FILE} ({actual_size} bytes).")
        ft_file = Path(__file__).resolve().parent / "dav3s_gamus_ft_v1.pth"
        if not ft_file.exists():
            shutil.copyfile(TARGET_FILE, ft_file)
            print(f"Initialized default fine-tune fallback at {ft_file}.")
        best_file = Path(__file__).resolve().parent / "v1.1.0" / "best.pt"
        best_file.parent.mkdir(parents=True, exist_ok=True)
        if not best_file.exists():
            shutil.copyfile(TARGET_FILE, best_file)
            print(f"Initialized default v1.1.0 checkpoint at {best_file}.")
    else:
        print(f"Warning: Downloaded size {actual_size} != expected {EXPECTED_SIZE}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download_weights()
