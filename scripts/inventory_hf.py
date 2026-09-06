import json
from collections import defaultdict
from pathlib import Path
from huggingface_hub import HfApi

api = HfApi()
repo_id = "earthflow/GAMUS"
print(f"Fetching file list for {repo_id}...")
files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")

out_txt = Path("artifacts/v1.1.0/hf_file_list.txt")
out_txt.write_text("\n".join(files), encoding="utf-8")
print(f"Saved {len(files)} files to {out_txt}")

# Compute inventory
# GAMUS files are typically images/{train,val,test}/*_RGB.h5, heights/.../*_AGL.h5, classes/.../*_CLS.h5
inventory = {
    "repo_id": repo_id,
    "total_files": len(files),
    "top_level_dirs": defaultdict(int),
    "splits_per_top_level": defaultdict(lambda: defaultdict(int)),
    "city_prefixes": defaultdict(int),
    "city_prefixes_by_modality": defaultdict(lambda: defaultdict(int)),
    "city_prefixes_by_split": defaultdict(lambda: defaultdict(int)),
    "non_data_files": []
}

for f in files:
    parts = f.split("/")
    if len(parts) >= 3 and parts[0] in ["images", "heights", "classes"]:
        top_dir = parts[0]
        split = parts[1]
        basename = parts[2]
        inventory["top_level_dirs"][top_dir] += 1
        inventory["splits_per_top_level"][top_dir][split] += 1
        
        # Discover city prefix: leading token before first underscore
        # E.g., DC_01_25_RGB.h5 -> DC
        # JAX_... -> JAX
        # OMA_... -> OMA
        # Check NYC / Philadelphia tokens
        city_token = basename.split("_")[0]
        inventory["city_prefixes"][city_token] += 1
        inventory["city_prefixes_by_modality"][top_dir][city_token] += 1
        inventory["city_prefixes_by_split"][split][city_token] += 1
    else:
        inventory["non_data_files"].append(f)
        if len(parts) > 1:
            inventory["top_level_dirs"][parts[0]] += 1
        else:
            inventory["top_level_dirs"]["[root]"] += 1

# Convert defaultdicts to normal dicts
def to_dict(d):
    if isinstance(d, defaultdict) or isinstance(d, dict):
        return {k: to_dict(v) for k, v in d.items()}
    return d

inventory_dict = to_dict(inventory)
out_json = Path("artifacts/v1.1.0/hf_inventory.json")
out_json.write_text(json.dumps(inventory_dict, indent=2), encoding="utf-8")
print(f"Saved inventory to {out_json}")

print("Summary:")
print(f"  Total files: {inventory['total_files']}")
print(f"  Top level dirs: {dict(inventory['top_level_dirs'])}")
print(f"  Splits per top level: {to_dict(inventory['splits_per_top_level'])}")
print(f"  City prefixes: {dict(inventory['city_prefixes'])}")
print(f"  City prefixes by split: {to_dict(inventory['city_prefixes_by_split'])}")
print(f"  Non data files: {inventory['non_data_files']}")
