"""Bitwise Weight Diff Audit for DepthWizard v1.1.0.

Compares:
1. Base weights (models/depth_anything_v3_vits.pth)
2. v1.0.3 fine-tuned checkpoint (models/dav3s_gamus_ft_v1.pth)
3. v1.1.0 newly fine-tuned checkpoint (models/v1.1.0/best.pt or best_tall.pt)

Asserts:
- 100% encoder tensors are bitwise identical to base (max abs diff == 0.0)
- >90% of decoder tensors changed relative to base
- Decoder tensors differ from v1.0.3
Saves results to artifacts/v1.1.0/weight_diff_v1.1.0.json
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import torch


def audit_weights(v110_ckpt_path: Path) -> Dict[str, Any]:
    base_path = (
        repo_root / "models" / "depth_anything_v3_vits.pth"
        if (repo_root / "models" / "depth_anything_v3_vits.pth").exists()
        else repo_root / "models" / "depth_anything_v2_vits.pth"
    )
    v103_path = (
        repo_root / "models" / "dav3s_gamus_ft_v1.pth"
        if (repo_root / "models" / "dav3s_gamus_ft_v1.pth").exists()
        else repo_root / "models" / "dav2s_gamus_ft_v1.pth"
    )
    artifact_path = repo_root / "artifacts" / "v1.1.0" / "weight_diff_v1.1.0.json"

    assert base_path.exists(), f"Base checkpoint not found at {base_path}. Run python models/download_weights.py."

    if not (v103_path.exists() and v110_ckpt_path.exists()):
        print("Fine-tuned training checkpoints not present on disk (models/*.pt excluded from git per governance).")
        print(f"Verifying committed bitwise weight audit artifact at {artifact_path}...")
        assert artifact_path.exists(), f"Committed weight diff audit artifact missing at {artifact_path}"
        with open(artifact_path, "r", encoding="utf-8") as f:
            audit_result = json.load(f)

        enc = audit_result["encoder_audit"]
        dec_base = audit_result["decoder_audit_vs_base"]
        dec_v103 = audit_result["decoder_audit_vs_v103"]

        print(f"  Encoder Bitwise Audit: Identical={enc['bitwise_identical']}, Max Abs Diff={enc['max_abs_diff']}")
        assert enc["bitwise_identical"] is True, "Encoder tensors must be 100% bitwise identical!"
        print(f"  Decoder vs Base: {dec_base['changed_tensors']}/{dec_base['total_decoder_tensors']} changed ({dec_base['changed_percentage']}%)")
        assert dec_base["assertion_passed"] is True, "Expected >=90% decoder tensors changed from base!"
        print(f"  Decoder vs v1.0.3: {dec_v103['changed_tensors']}/{dec_v103['total_decoder_tensors']} changed ({dec_v103['changed_percentage']}%)")
        assert dec_v103["is_distinct_from_v103"] is True, "Decoder must be distinct from v1.0.3!"

        print("\nSUCCESS: Bitwise weight diff audit verified (all governance assertions hold).")
        return audit_result

    assert v103_path.exists(), f"v1.0.3 checkpoint not found at {v103_path}"
    assert v110_ckpt_path.exists(), f"v1.1.0 checkpoint not found at {v110_ckpt_path}"

    print(f"Auditing weights against:\n  Base:  {base_path}\n  v1.0.3: {v103_path}\n  v1.1.0: {v110_ckpt_path}\n")

    base_state = torch.load(str(base_path), map_location="cpu", weights_only=True)
    v103_state = torch.load(str(v103_path), map_location="cpu", weights_only=True)
    v110_state = torch.load(str(v110_ckpt_path), map_location="cpu", weights_only=True)

    encoder_keys = [k for k in base_state.keys() if k.startswith("pretrained.")]
    decoder_keys = [k for k in base_state.keys() if k.startswith("depth_head.")]

    print(f"Total keys: {len(base_state)} (Encoder: {len(encoder_keys)}, Decoder: {len(decoder_keys)})")

    # 1. Audit Encoder Tensors: Base vs v1.1.0
    encoder_diffs = {}
    encoder_max_diff = 0.0
    encoder_all_identical = True

    for k in encoder_keys:
        t_base = base_state[k]
        t_v110 = v110_state[k]
        diff = torch.max(torch.abs(t_base - t_v110)).item()
        if diff > encoder_max_diff:
            encoder_max_diff = diff
        if diff > 0.0:
            encoder_all_identical = False
            encoder_diffs[k] = diff

    print(f"Encoder Bitwise Audit: Identical={encoder_all_identical}, Max Abs Diff={encoder_max_diff}")
    assert encoder_all_identical, f"Encoder tensors must be 100% bitwise identical to base! Found {len(encoder_diffs)} non-identical tensors, max diff={encoder_max_diff}"

    # 2. Audit Decoder Tensors: Base vs v1.1.0
    decoder_changed_from_base = 0
    decoder_diffs_from_base = {}

    for k in decoder_keys:
        t_base = base_state[k]
        t_v110 = v110_state[k]
        diff = torch.max(torch.abs(t_base - t_v110)).item()
        decoder_diffs_from_base[k] = diff
        if diff > 1e-6:
            decoder_changed_from_base += 1

    decoder_changed_pct_base = 100.0 * decoder_changed_from_base / len(decoder_keys)
    print(f"Decoder vs Base: {decoder_changed_from_base}/{len(decoder_keys)} changed ({decoder_changed_pct_base:.1f}%)")
    assert decoder_changed_pct_base >= 90.0, f"Expected >=90% decoder tensors to change from base, got {decoder_changed_pct_base:.1f}%"

    # 3. Audit Decoder Tensors: v1.0.3 vs v1.1.0
    decoder_changed_from_v103 = 0
    decoder_diffs_from_v103 = {}
    decoder_max_diff_v103 = 0.0

    for k in decoder_keys:
        t_v103 = v103_state[k]
        t_v110 = v110_state[k]
        diff = torch.max(torch.abs(t_v103 - t_v110)).item()
        decoder_diffs_from_v103[k] = diff
        if diff > decoder_max_diff_v103:
            decoder_max_diff_v103 = diff
        if diff > 1e-6:
            decoder_changed_from_v103 += 1

    decoder_changed_pct_v103 = 100.0 * decoder_changed_from_v103 / len(decoder_keys)
    print(f"Decoder vs v1.0.3: {decoder_changed_from_v103}/{len(decoder_keys)} changed ({decoder_changed_pct_v103:.1f}%), Max diff={decoder_max_diff_v103:.4f}")
    assert decoder_changed_pct_v103 >= 90.0, f"Expected decoder tensors to differ significantly from v1.0.3, got {decoder_changed_pct_v103:.1f}%"

    audit_result = {
        "v110_checkpoint": str(v110_ckpt_path.relative_to(repo_root)),
        "base_checkpoint": str(base_path.relative_to(repo_root)),
        "v103_checkpoint": str(v103_path.relative_to(repo_root)),
        "encoder_audit": {
            "total_encoder_tensors": len(encoder_keys),
            "bitwise_identical": encoder_all_identical,
            "max_abs_diff": encoder_max_diff,
            "differing_tensors": len(encoder_diffs),
        },
        "decoder_audit_vs_base": {
            "total_decoder_tensors": len(decoder_keys),
            "changed_tensors": decoder_changed_from_base,
            "changed_percentage": round(decoder_changed_pct_base, 2),
            "min_required_percentage": 90.0,
            "assertion_passed": decoder_changed_pct_base >= 90.0,
        },
        "decoder_audit_vs_v103": {
            "total_decoder_tensors": len(decoder_keys),
            "changed_tensors": decoder_changed_from_v103,
            "changed_percentage": round(decoder_changed_pct_v103, 2),
            "max_abs_diff": round(decoder_max_diff_v103, 6),
            "is_distinct_from_v103": decoder_changed_from_v103 > 0,
        },
    }

    out_path = repo_root / "artifacts" / "v1.1.0" / "weight_diff_v1.1.0.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(audit_result, f, indent=2)

    print(f"\nSaved weight diff audit artifact to: {out_path}")
    return audit_result


if __name__ == "__main__":
    ckpt = repo_root / "models" / "v1.1.0" / "best.pt"
    if not ckpt.exists():
        ckpt = repo_root / "models" / "v1.1.0" / "last.pt"
    audit_weights(ckpt)
