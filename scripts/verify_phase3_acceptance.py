import csv, json
from pathlib import Path

data_dir = Path("X:/DepthWizard SIH26175/data")
manifest_csv = data_dir / "gamus/manifest.csv"
qc_json = Path("artifacts/v1.1.0/data_qc_report.json")
stats_json = Path("artifacts/v1.1.0/dataset_stats_v1.1.0.json")
plot_png = Path("artifacts/v1.1.0/height_distribution.png")

# 1. Zero OMA or JAX files anywhere under data/
oma_jax_files = []
for p in data_dir.rglob("*"):
    name = p.name.upper()
    if "OMA" in name or "JAX" in name:
        oma_jax_files.append(str(p))

print("=== PHASE 3 ACCEPTANCE VERIFICATION ===")
print(f"1. OMA / JAX files found under data/: {len(oma_jax_files)}")
assert len(oma_jax_files) == 0, f"Found {len(oma_jax_files)} OMA/JAX files!"

# 2. Manifest and on-disk counts
with open(manifest_csv, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

disk_crops = {
    "train": list((data_dir / "gamus/train").glob("*.npz")),
    "val": list((data_dir / "gamus/val").glob("*.npz")),
    "test": list((data_dir / "gamus/test").glob("*.npz")),
}
total_disk_crops = sum(len(v) for v in disk_crops.values())

print(f"2. Manifest row count: {len(rows)}")
print(f"   On-disk crop count: {total_disk_crops}")
print(f"   Breakdown on disk: train={len(disk_crops['train'])}, val={len(disk_crops['val'])}, test={len(disk_crops['test'])}")
assert len(rows) == total_disk_crops, f"Manifest rows ({len(rows)}) != disk crops ({total_disk_crops})"
assert len(disk_crops["train"]) >= 3000, f"Train count {len(disk_crops['train'])} < 3000"
assert len(disk_crops["val"]) >= 400, f"Val count {len(disk_crops['val'])} < 400"
assert len(disk_crops["test"]) >= 900, f"Test count {len(disk_crops['test'])} < 900"

# 3. Official split boundary integrity and zero split intersections
split_tiles = {"train": set(), "val": set(), "test": set()}
for r in rows:
    split_tiles[r["split"]].add(r["source_tile"])

inter_tv = split_tiles["train"] & split_tiles["val"]
inter_tt = split_tiles["train"] & split_tiles["test"]
inter_vt = split_tiles["val"] & split_tiles["test"]

print(f"3. Split intersection sizes:")
print(f"   Train & Val: {len(inter_tv)}")
print(f"   Train & Test: {len(inter_tt)}")
print(f"   Val & Test: {len(inter_vt)}")
assert len(inter_tv) == 0
assert len(inter_tt) == 0
assert len(inter_vt) == 0

# 4. QC Report
assert qc_json.exists()
with open(qc_json) as f:
    qc_data = json.load(f)
print(f"4. QC Report exists: {qc_json}")
print(f"   Total QC events: {qc_data['total_qc_events']}")
print(f"   Per-reason counts: {qc_data['by_reason']}")

# 5. Dataset Stats and Histogram
assert stats_json.exists()
assert plot_png.exists()
with open(stats_json) as f:
    stats_data = json.load(f)
print(f"5. Dataset stats exists: {stats_json}")
print(f"   Height distribution plot exists: {plot_png}")
print(f"   Measured tall-pixel (>=15 m) fractions:")
for city, info in stats_data["city_pixel_totals"].items():
    print(f"     {city}: {info['tall_fraction_pct']}% ({info['tall_pixels_ge_15m']:,} / {info['total_valid_pixels']:,} px)")

print("\n>>> ALL PHASE 3 ACCEPTANCE CRITERIA MET AND VERIFIED <<<")
