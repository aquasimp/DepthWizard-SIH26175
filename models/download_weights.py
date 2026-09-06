#!/usr/bin/env python3
"""Cross-platform weight downloader for Depth Anything V2 Small."""

import os
import sys
import urllib.request
from pathlib import Path

TARGET_FILE = Path(__file__).resolve().parent / "depth_anything_v2_vits.pth"
EXPECTED_SIZE = 99218434
URL = "https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/main/depth_anything_v2_vits.pth"


def download_weights() -> None:
    if TARGET_FILE.exists():
        actual_size = TARGET_FILE.stat().st_size
        if actual_size == EXPECTED_SIZE:
            print(f"Weights file already exists and size matches ({EXPECTED_SIZE} bytes): {TARGET_FILE}")
            sys.exit(0)
        else:
            print(f"Weights file exists but size ({actual_size}) != expected ({EXPECTED_SIZE}). Re-downloading...")

    print(f"Downloading Depth Anything V2 Small weights ({EXPECTED_SIZE / 1e6:.1f} MB) from Hugging Face...")
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0 and count % 500 == 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\r  Progress: {min(100, percent)}% [{count * block_size / 1e6:.1f} MB / {total_size / 1e6:.1f} MB]")
                sys.stdout.flush()

        urllib.request.urlretrieve(URL, str(TARGET_FILE), reporthook=reporthook)
        print()
    except Exception as e:
        print(f"\nError downloading weights: {e}", file=sys.stderr)
        sys.exit(1)

    actual_size = TARGET_FILE.stat().st_size
    if actual_size == EXPECTED_SIZE:
        print(f"Successfully downloaded {TARGET_FILE} ({actual_size} bytes).")
    else:
        print(f"Warning: Downloaded size {actual_size} != expected {EXPECTED_SIZE}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    download_weights()
