"""Verify scope fence by comparing current file hashes against artifacts/v1.1.0/fence_hashes_before.json."""

import hashlib
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_fence():
    before_hashes_path = repo_root / "artifacts" / "v1.1.0" / "fence_hashes_before.json"
    assert before_hashes_path.exists(), f"Missing before hashes artifact at {before_hashes_path}"

    with open(before_hashes_path, "r", encoding="utf-8") as f:
        before_hashes = json.load(f)

    after_hashes = {}
    violations = []

    for rel_path, expected_hash in before_hashes.items():
        full_path = repo_root / rel_path
        if not full_path.exists():
            violations.append(f"DELETED: {rel_path}")
            continue

        curr_hash = compute_sha256(full_path)
        after_hashes[rel_path] = curr_hash
        if curr_hash != expected_hash:
            violations.append(f"MODIFIED: {rel_path} (expected {expected_hash[:12]}..., got {curr_hash[:12]}...)")

    after_hashes_path = repo_root / "artifacts" / "v1.1.0" / "fence_hashes_after.json"
    with open(after_hashes_path, "w", encoding="utf-8") as f:
        json.dump(after_hashes, f, indent=2)

    print(f"Verified {len(before_hashes)} fenced files.")
    if violations:
        print(f"FAILED: {len(violations)} scope fence violations detected:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("SUCCESS: 100% of fenced files match their pre-v1.1.0 hashes (0 violations).")


if __name__ == "__main__":
    verify_fence()
