import json
from pathlib import Path
from huggingface_hub import hf_hub_download

repo_id = "earthflow/GAMUS"
sample_files = [
    "images/train/DC_01_25_RGB.h5",
    "heights/train/DC_01_25_AGL.h5",
    "classes/train/DC_01_25_CLS.h5"
]

target_dir = Path("artifacts/v1.1.0/sample_triplet")
target_dir.mkdir(parents=True, exist_ok=True)

measured_sizes = {}
total_bytes = 0

for hf_subpath in sample_files:
    print(f"Downloading {hf_subpath} from {repo_id}...")
    local_path = hf_hub_download(
        repo_id=repo_id,
        filename=hf_subpath,
        repo_type="dataset",
        local_dir=str(target_dir),
        local_dir_use_symlinks=False
    )
    p = Path(local_path)
    size = p.stat().st_size
    measured_sizes[hf_subpath] = {
        "local_path": str(p),
        "size_bytes": size,
        "size_kb": round(size / 1024, 2),
        "size_mb": round(size / (1024 * 1024), 4)
    }
    total_bytes += size
    print(f"  -> {p.name}: {size} bytes ({round(size / 1024, 2)} KB)")

summary = {
    "repo_id": repo_id,
    "triplet_basename": "DC_01_25",
    "files": measured_sizes,
    "total_triplet_bytes": total_bytes,
    "total_triplet_kb": round(total_bytes / 1024, 2),
    "total_triplet_mb": round(total_bytes / (1024 * 1024), 4)
}

out_json = Path("artifacts/v1.1.0/sample_triplet_bytes.json")
out_json.write_text(json.dumps(summary, indent=2))
print(f"\nTotal triplet size: {total_bytes} bytes ({round(total_bytes / (1024 * 1024), 4)} MB)")
print(f"Saved size record to {out_json}")
