"""Timing probe for DepthWizard v1.1.0 fine-tuning run.

Measures:
1. Encoder frozen confirmation (requires_grad=False)
2. Largest micro-batch fitting 6 GB VRAM under AMP (testing 8, 6, 4, 2)
3. Step seconds over 30 real steps
4. 1 full epoch wall-clock time (train + val)
Saves results to artifacts/v1.1.0/timing_probe.json
"""

import gc
import json
import math
import sys
import time
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import numpy as np
import torch
from depthwizard.depth.backbone import DepthAnythingV2Small, load_dav2_small
from torch.utils.data import DataLoader

from training.dataset import GAMUSDataset
from training.losses import MetricNDSMLoss
from training.sampler import HeightStratifiedBatchSampler
from training.train_head import configure_trainable_parameters


def run_probe():
    assert torch.cuda.is_available(), "CUDA must be available for timing probe"
    device = "cuda"
    device_name = torch.cuda.get_device_name(0)
    total_vram_mb = torch.cuda.get_device_properties(0).total_memory / (1024**2)
    print(f"CUDA Device: {device_name} ({total_vram_mb:.1f} MB VRAM)")

    # 1. Model loading & freeze check
    checkpoint_path = repo_root / "models" / "depth_anything_v2_vits.pth"
    print(f"Loading base model: {checkpoint_path}")
    model = load_dav2_small(checkpoint_path, device=device)

    # Scale output convolution weights if starting from raw base relative model
    model.depth_head.scratch.output_conv2[2].weight.data *= 58.0
    model.depth_head.scratch.output_conv2[2].bias.data *= 58.0

    trainable_params, trainable_count, frozen_count = configure_trainable_parameters(model)
    encoder_all_frozen = all(not p.requires_grad for p in model.pretrained.parameters())
    decoder_all_trainable = all(p.requires_grad for p in model.depth_head.parameters())

    print(f"Encoder all frozen: {encoder_all_frozen} ({frozen_count:,} params)")
    print(f"Decoder all trainable: {decoder_all_trainable} ({trainable_count:,} params)")
    assert encoder_all_frozen, "Encoder parameters must all be frozen (requires_grad=False)!"
    assert decoder_all_trainable, "Decoder parameters must all be trainable (requires_grad=True)!"

    # 2. Test micro-batch sizes under AMP
    candidate_batches = [8, 6, 4, 2]
    vram_results = {}
    largest_working_batch = None

    criterion = MetricNDSMLoss(lambd=0.85, eps=1e-4).to(device)

    for b in candidate_batches:
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        optimizer = torch.optim.AdamW(trainable_params, lr=3e-5, weight_decay=0.01)
        scaler = torch.amp.GradScaler("cuda", enabled=True)

        try:
            print(f"Testing batch size {b} under AMP...")
            # Run 3 test iterations
            for _ in range(3):
                optimizer.zero_grad()
                dummy_x = torch.randn(b, 3, 518, 518, device=device)
                dummy_y = torch.rand(b, 1, 518, 518, device=device) * 40.0
                dummy_m = torch.ones(b, 1, 518, 518, dtype=torch.bool, device=device)

                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    with torch.no_grad():
                        feats = model.pretrained(dummy_x)
                    preds = model.depth_head(feats, 37, 37)
                    loss = criterion(preds, dummy_y, dummy_m)

                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()

            torch.cuda.synchronize()
            peak_mb = torch.cuda.max_memory_allocated() / (1024**2)
            vram_results[str(b)] = {
                "batch_size": b,
                "fits": True,
                "peak_vram_mb": round(peak_mb, 2),
                "headroom_mb": round(total_vram_mb - peak_mb, 2),
            }
            print(f"  Batch size {b}: SUCCESS. Peak VRAM: {peak_mb:.1f} MB (Headroom: {total_vram_mb - peak_mb:.1f} MB)")
            if largest_working_batch is None:
                largest_working_batch = b
        except torch.cuda.OutOfMemoryError:
            print(f"  Batch size {b}: OOM")
            vram_results[str(b)] = {
                "batch_size": b,
                "fits": False,
                "peak_vram_mb": None,
                "headroom_mb": 0.0,
            }
            torch.cuda.empty_cache()

    print(f"Largest workable micro-batch size: {largest_working_batch}")
    assert largest_working_batch is not None, "At least one batch size must fit in 6 GB VRAM"

    # 3. Real Step Seconds Benchmark (30 steps)
    chosen_batch = largest_working_batch
    manifest_path = repo_root / "data" / "gamus" / "manifest.csv"
    train_ds = GAMUSDataset(manifest_path=manifest_path, split="train", crop_size=518, augment=True)
    val_ds = GAMUSDataset(manifest_path=manifest_path, split="val", crop_size=518, augment=False)

    train_sampler = HeightStratifiedBatchSampler(
        manifest_path=manifest_path,
        batch_size=chosen_batch,
        accumulation_steps=1,
        seed=1337,
    )
    train_loader = DataLoader(
        train_ds,
        batch_sampler=train_sampler,
        num_workers=0,
        pin_memory=True,
    )

    optimizer = torch.optim.AdamW(trainable_params, lr=3e-5, weight_decay=0.01)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    print(f"\nBenchmarking 30 real training steps with batch_size={chosen_batch}...")
    model.depth_head.train()
    model.pretrained.eval()

    step_times = []
    step_count = 0

    # Warmup 5 steps
    loader_iter = iter(train_loader)
    for _ in range(5):
        batch = next(loader_iter)
        img = batch["image"].to(device, non_blocking=True)
        tgt = batch["depth"].to(device, non_blocking=True)
        msk = batch["mask"].to(device, non_blocking=True)

        optimizer.zero_grad()
        with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
            with torch.no_grad():
                feats = model.pretrained(img)
            preds = model.depth_head(feats, 37, 37)
            loss = criterion(preds, tgt, msk)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()

    torch.cuda.synchronize()

    # Time 30 steps
    for _ in range(30):
        t0 = time.perf_counter()
        batch = next(loader_iter)
        img = batch["image"].to(device, non_blocking=True)
        tgt = batch["depth"].to(device, non_blocking=True)
        msk = batch["mask"].to(device, non_blocking=True)

        optimizer.zero_grad()
        with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
            with torch.no_grad():
                feats = model.pretrained(img)
            preds = model.depth_head(feats, 37, 37)
            loss = criterion(preds, tgt, msk)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        step_times.append(dt)

    step_stats = {
        "mean_s": round(float(np.mean(step_times)), 4),
        "median_s": round(float(np.median(step_times)), 4),
        "min_s": round(float(np.min(step_times)), 4),
        "max_s": round(float(np.max(step_times)), 4),
        "std_s": round(float(np.std(step_times)), 4),
    }
    print(f"Step timing (30 steps): mean={step_stats['mean_s']}s, median={step_stats['median_s']}s, min={step_stats['min_s']}s, max={step_stats['max_s']}s")

    # 4. Measure 1 full epoch wall-clock (train + val)
    print("\nMeasuring 1 full epoch wall-clock (train + val)...")
    epoch_t0 = time.perf_counter()

    # Train pass
    model.depth_head.train()
    model.pretrained.eval()
    train_t0 = time.perf_counter()
    n_train_batches = len(train_loader)
    train_losses = []

    for batch_idx, batch in enumerate(train_loader):
        img = batch["image"].to(device, non_blocking=True)
        tgt = batch["depth"].to(device, non_blocking=True)
        msk = batch["mask"].to(device, non_blocking=True)

        optimizer.zero_grad()
        with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
            with torch.no_grad():
                feats = model.pretrained(img)
            preds = model.depth_head(feats, 37, 37)
            loss = criterion(preds, tgt, msk)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
        scaler.step(optimizer)
        scaler.update()
        train_losses.append(loss.item())

        if (batch_idx + 1) % 100 == 0 or (batch_idx + 1) == n_train_batches:
            print(f"  Train batch {batch_idx + 1}/{n_train_batches} ({100*(batch_idx+1)/n_train_batches:.1f}%)")

    torch.cuda.synchronize()
    train_epoch_s = time.perf_counter() - train_t0

    # Val pass
    val_loader = DataLoader(
        val_ds,
        batch_size=chosen_batch,
        shuffle=False,
        num_workers=0,
        pin_memory=True,
    )
    val_t0 = time.perf_counter()
    model.depth_head.eval()
    n_val_batches = len(val_loader)
    val_losses = []

    with torch.no_grad():
        for batch_idx, batch in enumerate(val_loader):
            img = batch["image"].to(device, non_blocking=True)
            tgt = batch["depth"].to(device, non_blocking=True)
            msk = batch["mask"].to(device, non_blocking=True)

            with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                feats = model.pretrained(img)
                preds = model.depth_head(feats, 37, 37)
                loss = criterion(preds, tgt, msk)
            val_losses.append(loss.item())

    torch.cuda.synchronize()
    val_epoch_s = time.perf_counter() - val_t0
    total_epoch_s = time.perf_counter() - epoch_t0

    print(f"\n1 Full Epoch wall-clock: {total_epoch_s:.2f} s")
    print(f"  Train: {train_epoch_s:.2f} s ({n_train_batches} batches, ~{train_epoch_s/n_train_batches:.4f} s/batch)")
    print(f"  Val:   {val_epoch_s:.2f} s ({n_val_batches} batches, ~{val_epoch_s/n_val_batches:.4f} s/batch)")

    # 5. Compute epoch count formula
    # N_epochs = clamp(floor(9 * 3600 / epoch_seconds), 30, 80), preferred target ~60
    budget_seconds = 9 * 3600  # 9 hours
    raw_epochs = int(math.floor(budget_seconds / total_epoch_s))
    recommended_epochs = max(30, min(80, raw_epochs))
    # Preferred target ~60 if recommended_epochs allows
    target_epochs = 60 if 30 <= 60 <= recommended_epochs else recommended_epochs
    print(f"\nEpoch calculation:")
    print(f"  Raw budget epochs: {raw_epochs} epochs")
    print(f"  Clamped [30, 80]: {recommended_epochs} epochs")
    print(f"  Selected target epochs: {target_epochs} epochs (Est. runtime: {target_epochs * total_epoch_s / 60:.1f} min)")

    # 6. Save probe results
    probe_output = {
        "device": device_name,
        "total_vram_mb": round(total_vram_mb, 2),
        "encoder_frozen": encoder_all_frozen,
        "encoder_params_frozen": frozen_count,
        "decoder_params_trainable": trainable_count,
        "vram_tests": vram_results,
        "selected_batch_size": chosen_batch,
        "step_seconds_30steps": step_stats,
        "epoch_timing": {
            "total_epoch_seconds": round(total_epoch_s, 3),
            "train_epoch_seconds": round(train_epoch_s, 3),
            "val_epoch_seconds": round(val_epoch_s, 3),
            "train_batches": n_train_batches,
            "val_batches": n_val_batches,
        },
        "epoch_count_arithmetic": {
            "budget_hours": 9,
            "budget_seconds": budget_seconds,
            "raw_epochs": raw_epochs,
            "clamped_epochs": recommended_epochs,
            "target_epochs": target_epochs,
            "estimated_total_runtime_minutes": round(target_epochs * total_epoch_s / 60.0, 2),
            "estimated_total_runtime_hours": round(target_epochs * total_epoch_s / 3600.0, 2),
        },
    }

    out_path = repo_root / "artifacts" / "v1.1.0" / "timing_probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(probe_output, f, indent=2)

    print(f"\nSaved timing probe artifact to: {out_path}")


if __name__ == "__main__":
    run_probe()
