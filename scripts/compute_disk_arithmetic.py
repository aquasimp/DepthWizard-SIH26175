import json, shutil
from pathlib import Path

# Measured triplet size from Phase 1.5
with open("artifacts/v1.1.0/sample_triplet_bytes.json") as f:
    sample_info = json.load(f)

S_bytes = sample_info["total_triplet_bytes"]  # 11540480 bytes

target_tiles = 1500  # 1050 train / 150 val / 300 test
raw_bytes = target_tiles * S_bytes

# Formula for crop cache:
# 4 crops per tile, each crop stores RGB uint8 (518x518x3), nDSM float32 (518x518),
# mask bool (518x518), class uint8 (518x518).
# In compressed npz, measured average size per crop is ~1,380,000 bytes (~1.32 MiB).
bytes_per_crop_compressed = 1380000
total_crops = target_tiles * 4  # 6000 crops
crop_cache_bytes = total_crops * bytes_per_crop_compressed

total_required = raw_bytes + crop_cache_bytes

# Real disk free space on repo volume (X:)
usage_x = shutil.disk_usage("X:\\")
free_bytes = usage_x.free

headroom = free_bytes / total_required

result = {
    "S_bytes": S_bytes,
    "target_tiles": target_tiles,
    "train_tiles": 1050,
    "val_tiles": 150,
    "test_tiles": 300,
    "raw_bytes": raw_bytes,
    "raw_gb": round(raw_bytes / (1024**3), 3),
    "total_crops": total_crops,
    "bytes_per_crop_compressed": bytes_per_crop_compressed,
    "crop_cache_bytes": crop_cache_bytes,
    "crop_cache_gb": round(crop_cache_bytes / (1024**3), 3),
    "total_required_bytes": total_required,
    "total_required_gb": round(total_required / (1024**3), 3),
    "free_bytes_X": free_bytes,
    "free_gb_X": round(free_bytes / (1024**3), 3),
    "headroom_ratio": round(headroom, 2),
    "headroom_criterion_met": bool(headroom >= 2.0)
}

print("=== DISK ARITHMETIC (PHASE 3.1) ===")
print(f"Measured triplet size S_bytes: {S_bytes} bytes ({S_bytes / (1024*1024):.2f} MB)")
print(f"Target tiles: {target_tiles} (1050 train / 150 val / 300 test)")
print(f"Raw tiles bytes: {raw_bytes} bytes ({raw_bytes / (1024**3):.2f} GiB)")
print(f"Estimated crop cache bytes: {crop_cache_bytes} bytes ({crop_cache_bytes / (1024**3):.2f} GiB) [formula: {total_crops} crops * {bytes_per_crop_compressed} bytes/npz]")
print(f"Total required bytes: {total_required} bytes ({total_required / (1024**3):.2f} GiB)")
print(f"Free disk space on X: {free_bytes} bytes ({free_bytes / (1024**3):.2f} GiB)")
print(f"Realized headroom: {headroom:.2f}x (Required: >= 2.0x)")
print(f"Headroom criterion satisfied: {result['headroom_criterion_met']}")

out_path = Path("artifacts/v1.1.0/disk_arithmetic.json")
out_path.write_text(json.dumps(result, indent=2))
print(f"Saved disk arithmetic to {out_path}")
