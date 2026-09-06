import json
from pathlib import Path
import h5py
import numpy as np

sample_dir = Path("artifacts/v1.1.0/sample_triplet")

files = {
    "RGB": sample_dir / "images/train/DC_01_25_RGB.h5",
    "AGL": sample_dir / "heights/train/DC_01_25_AGL.h5",
    "CLS": sample_dir / "classes/train/DC_01_25_CLS.h5"
}

probe_results = {}

for modality, fpath in files.items():
    print(f"Probing {modality} at {fpath}...")
    with h5py.File(fpath, "r") as hf:
        keys = list(hf.keys())
        keys_info = {}
        for k in keys:
            arr = hf[k][()]
            nan_count = int(np.isnan(arr).sum()) if np.issubdtype(arr.dtype, np.floating) else 0
            
            # Non-nan values for min/max
            valid_arr = arr[~np.isnan(arr)] if nan_count > 0 else arr
            val_min = float(np.min(valid_arr)) if valid_arr.size > 0 else None
            val_max = float(np.max(valid_arr)) if valid_arr.size > 0 else None
            
            info = {
                "shape": list(arr.shape),
                "dtype": str(arr.dtype),
                "min": val_min,
                "max": val_max,
                "nan_count": nan_count,
                "total_elements": int(arr.size)
            }
            if modality == "CLS":
                unique_vals = [int(x) for x in np.unique(arr)]
                info["unique_values"] = unique_vals
                info["unique_value_counts"] = {int(k): int(v) for k, v in zip(*np.unique(arr, return_counts=True))}
            keys_info[k] = info
            
        probe_results[modality] = {
            "file": str(fpath),
            "keys": keys,
            "datasets": keys_info
        }

out_path = Path("artifacts/v1.1.0/h5_probe.json")
out_path.write_text(json.dumps(probe_results, indent=2))
print(f"Probe saved to {out_path}")
print(json.dumps(probe_results, indent=2))
