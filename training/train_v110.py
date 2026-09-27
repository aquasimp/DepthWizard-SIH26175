"""DepthWizard v1.1.0 Fine-Tuning Execution Script.

Controlled Experiment:
- Base: Depth Anything V3 Small relative depth base model (models/depth_anything_v3_vits.pth)
- Architecture: Frozen DINOv2 ViT-S encoder (requires_grad=False), DPT head fine-tuning
- Loss: MetricNDSMLoss (SiLog lambda=0.85, eps=1e-4) - unchanged
- Controlled Variables (3):
  1. Data scale-up: 3,817 train crops across 3 cities (DC, NYC, PHL)
  2. Sampler: HeightStratifiedBatchSampler (2.5x tall structure enrichment)
  3. Augmentation: Synchronized height-safe spatial flips, rot90, and photometric jitter
"""

import argparse
import csv
import json
import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

import matplotlib.pyplot as plt
import numpy as np
import torch
import yaml
from depthwizard.depth.backbone import DepthAnythingV3Small, load_dav3_small
from torch.utils.data import DataLoader

from training.dataset import GAMUSDataset
from training.losses import MetricNDSMLoss
from training.sampler import HeightStratifiedBatchSampler
from training.train_head import configure_trainable_parameters


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DepthWizard v1.1.0 Fine-Tuning Run")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/v1.1.0-train.yaml",
        help="Path to YAML training configuration file.",
    )
    parser.add_argument("--epochs", type=int, default=None, help="Override number of epochs.")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size.")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate.")
    parser.add_argument("--device", type=str, default=None, help="Device to use ('cuda' or 'cpu').")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume fine-tuning from existing checkpoint in models/v1.1.0/last.pt",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run 2-epoch smoke test on subset to verify logging and checkpointing.",
    )
    return parser.parse_args()


def setup_logger(log_dir: Path, utc_timestamp: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"train_{utc_timestamp}.log"

    logger = logging.getLogger("v110_trainer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s UTC] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def train_v110(args: argparse.Namespace) -> Dict[str, Any]:
    start_wall_time = time.perf_counter()
    utc_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Load configuration
    config_path = Path(args.config)
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    # Resolve paths & overrides
    log_dir = repo_root / config.get("logging", {}).get("dir", "logs/v1.1.0")
    logger = setup_logger(log_dir, utc_str)
    logger.info(f"DepthWizard v1.1.0 Training Session Initialized. Config: {config_path}")

    ckpt_cfg = config.get("checkpoints", {})
    ckpt_dir = repo_root / ckpt_cfg.get("dir", "models/v1.1.0")
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    last_ckpt_path = repo_root / ckpt_cfg.get("last", "models/v1.1.0/last.pt")
    best_ckpt_path = repo_root / ckpt_cfg.get("best", "models/v1.1.0/best.pt")
    best_tall_ckpt_path = repo_root / ckpt_cfg.get("best_tall", "models/v1.1.0/best_tall.pt")

    jsonl_log = repo_root / config.get("logging", {}).get("jsonl", "logs/v1.1.0/train_metrics.jsonl")
    csv_log = repo_root / config.get("logging", {}).get("csv", "logs/v1.1.0/train_metrics.csv")
    jsonl_log.parent.mkdir(parents=True, exist_ok=True)
    csv_log.parent.mkdir(parents=True, exist_ok=True)

    # Hyperparameters
    t_cfg = config.get("training", {})
    epochs = args.epochs or (2 if args.smoke else t_cfg.get("epochs", 60))
    batch_size = args.batch_size or config.get("data", {}).get("batch_size", 8)
    base_lr = args.lr or float(t_cfg.get("learning_rate", 3e-5))
    min_lr = float(t_cfg.get("min_lr", 3e-6))
    warmup_ratio = float(t_cfg.get("warmup_ratio", 0.05))
    weight_decay = float(t_cfg.get("weight_decay", 0.01))
    grad_clip = float(t_cfg.get("grad_clip", 1.0))
    use_amp = bool(t_cfg.get("amp", True)) and torch.cuda.is_available()
    seed = int(t_cfg.get("seed", 1337))

    device_str = args.device or t_cfg.get("device", "cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(device_str)

    # Set seeds
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    logger.info(f"Target Device: {device} ({torch.cuda.get_device_name(0) if device.type == 'cuda' else 'CPU'})")
    logger.info(f"Parameters: epochs={epochs}, batch_size={batch_size}, lr={base_lr}, amp={use_amp}, seed={seed}, smoke={args.smoke}")

    # Model Setup
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True

    if args.resume and last_ckpt_path.exists():
        logger.info(f"Resuming model weights from existing checkpoint: {last_ckpt_path}")
        model = load_dav3_small(last_ckpt_path, device=str(device))
    else:
        init_ckpt = repo_root / config.get("model", {}).get("init_checkpoint", "models/depth_anything_v3_vits.pth")
        logger.info(f"Loading base weights from: {init_ckpt}")
        model = load_dav3_small(init_ckpt, device=str(device))

        # Scale output convolution weights if starting from raw base relative model
        if "depth_anything_v3_vits.pth" in str(init_ckpt) or "depth_anything_v2_vits.pth" in str(init_ckpt):
            logger.info("Initializing metric elevation head: scaling output_conv2[2] weights and bias by 58.0")
            model.depth_head.scratch.output_conv2[2].weight.data *= 58.0
            model.depth_head.scratch.output_conv2[2].bias.data *= 58.0

    # Configure parameters
    trainable_params, trainable_count, frozen_count = configure_trainable_parameters(model)
    encoder_all_frozen = all(not p.requires_grad for p in model.pretrained.parameters())
    decoder_all_trainable = all(p.requires_grad for p in model.depth_head.parameters())
    assert encoder_all_frozen, "Encoder parameters must all be frozen (requires_grad=False)!"
    assert decoder_all_trainable, "Decoder parameters must all be trainable (requires_grad=True)!"
    logger.info(f"Architecture: {frozen_count:,} frozen encoder params, {trainable_count:,} trainable decoder params")

    # Dataset & Dataloader setup
    manifest_path = repo_root / config.get("data", {}).get("manifest", "data/gamus/manifest.csv")
    crop_size = config.get("data", {}).get("crop_size", 518)
    augment = bool(config.get("data", {}).get("augment", True))

    if args.smoke:
        # Create a small smoke manifest stratified with 50 crops from each bucket B0, B1, B2, B3 (200 train) and 50 val crops
        smoke_manifest_path = repo_root / "data" / "gamus" / "smoke_manifest_v110.csv"
        with open(manifest_path, "r", encoding="utf-8") as f_in:
            rows = list(csv.DictReader(f_in))

        b_rows = {"B0": [], "B1": [], "B2": [], "B3": []}
        for r in rows:
            if r.get("split") == "train":
                tf = float(r.get("band_15_30", 0.0)) + float(r.get("band_30_inf", 0.0))
                if tf < 0.01:
                    b_rows["B0"].append(r)
                elif tf < 0.05:
                    b_rows["B1"].append(r)
                elif tf < 0.15:
                    b_rows["B2"].append(r)
                else:
                    b_rows["B3"].append(r)

        train_rows = (
            b_rows["B0"][:50] + b_rows["B1"][:50] + b_rows["B2"][:50] + b_rows["B3"][:50]
        )
        val_rows = [r for r in rows if r.get("split") == "val"][:50]
        smoke_rows = train_rows + val_rows
        with open(smoke_manifest_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=list(smoke_rows[0].keys()))
            writer.writeheader()
            writer.writerows(smoke_rows)
        manifest_path = smoke_manifest_path
        logger.info(f"Smoke test mode enabled: Using {manifest_path} (200 train [50 B0, 50 B1, 50 B2, 50 B3], 50 val crops)")

    train_ds = GAMUSDataset(manifest_path=manifest_path, split="train", crop_size=crop_size, augment=augment)
    val_ds = GAMUSDataset(manifest_path=manifest_path, split="val", crop_size=crop_size, augment=False)

    train_sampler = HeightStratifiedBatchSampler(
        manifest_path=manifest_path,
        batch_size=batch_size,
        accumulation_steps=1,
        seed=seed,
    )
    train_loader = DataLoader(
        train_ds,
        batch_sampler=train_sampler,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )

    logger.info(f"Data Loaders Ready: {len(train_ds)} train crops ({len(train_loader)} batches/epoch), {len(val_ds)} val crops ({len(val_loader)} batches)")

    # Loss, Optimizer, Scheduler
    loss_cfg = t_cfg.get("loss", {})
    criterion = MetricNDSMLoss(
        lambd=float(loss_cfg.get("silog_lambda", 0.85)),
        eps=float(loss_cfg.get("silog_eps", 1e-4)),
    ).to(device)

    optimizer = torch.optim.AdamW(
        trainable_params,
        lr=base_lr,
        weight_decay=weight_decay,
    )

    total_steps = epochs * len(train_loader)
    warmup_steps = max(1, int(warmup_ratio * total_steps))

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        decay = 0.5 * (1.0 + math.cos(math.pi * progress))
        min_ratio = min_lr / base_lr if base_lr > 0 else 0.1
        return min_ratio + (1.0 - min_ratio) * decay

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    start_epoch = 1
    best_epoch = 0
    best_val_rmse = float("inf")
    best_val_rmse_tall = float("inf")
    current_step = 0

    history: Dict[str, List[Any]] = {
        "epochs": [],
        "train_loss": [],
        "train_rmse": [],
        "val_loss": [],
        "val_rmse": [],
        "val_rmse_tall": [],
        "lr": [],
    }

    prior_elapsed_sec = 0.0
    # If resuming, load existing metrics and fast-forward state
    if args.resume and csv_log.exists() and csv_log.stat().st_size > 0:
        logger.info(f"Reading existing training history from: {csv_log}")
        with open(csv_log, "r", encoding="utf-8") as f_csv:
            reader = csv.DictReader(f_csv)
            for r in reader:
                ep = int(r["epoch"])
                history["epochs"].append(ep)
                history["train_loss"].append(float(r["train_loss"]) if r["train_loss"] != "nan" else float("nan"))
                history["train_rmse"].append(float(r["train_rmse"]))
                history["val_loss"].append(float(r["val_loss"]) if r["val_loss"] != "nan" else float("nan"))
                v_rmse = float(r["val_rmse"])
                history["val_rmse"].append(v_rmse)
                v_rmse_tall = float(r["val_rmse_tall"])
                history["val_rmse_tall"].append(v_rmse_tall)
                history["lr"].append(float(r["lr"]))
                prior_elapsed_sec = float(r.get("elapsed_sec", 0.0))
                if v_rmse < best_val_rmse:
                    best_val_rmse = v_rmse
                    best_epoch = ep
                if v_rmse_tall < best_val_rmse_tall:
                    best_val_rmse_tall = v_rmse_tall

        if history["epochs"]:
            last_ep = max(history["epochs"])
            start_epoch = last_ep + 1
            current_step = last_ep * len(train_loader)
            logger.info(
                f"Resuming training at Epoch {start_epoch}/{epochs} (Step {current_step}). "
                f"Prior Best Val RMSE: {best_val_rmse:.3f}m (Epoch {best_epoch}), Best Tall RMSE: {best_val_rmse_tall:.3f}m"
            )
            # Advance scheduler to step
            for _ in range(current_step):
                scheduler.step()
    elif not csv_log.exists() or csv_log.stat().st_size == 0 or args.smoke:
        with open(csv_log, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "epoch",
                "step",
                "train_loss",
                "train_rmse",
                "train_mae",
                "val_loss",
                "val_rmse",
                "val_mae",
                "val_rmse_tall",
                "val_mae_tall",
                "val_tall_pixels",
                "lr",
                "epoch_sec",
                "elapsed_sec",
                "peak_vram_mb",
            ])

    # Training Loop
    logger.info(f"Beginning training from epoch {start_epoch} to {epochs}...")
    for epoch in range(start_epoch, epochs + 1):
        epoch_t0 = time.perf_counter()
        train_sampler.set_epoch(epoch)

        model.depth_head.train()
        model.pretrained.eval()

        train_batch_losses = []
        train_sq_err = 0.0
        train_abs_err = 0.0
        train_pixel_count = 0

        for batch_idx, batch in enumerate(train_loader):
            img = batch["image"].to(device, non_blocking=True)
            tgt = batch["depth"].to(device, non_blocking=True)
            msk = batch["mask"].to(device, non_blocking=True)

            optimizer.zero_grad()

            with torch.amp.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                with torch.no_grad():
                    features = model.pretrained(img)
                preds = model.depth_head(features, 37, 37)

            # Compute loss in fp32 for numerical stability
            loss = criterion(preds.float(), tgt.float(), msk)

            if use_amp:
                scale_before = scaler.get_scale()
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=grad_clip)
                scaler.step(optimizer)
                scaler.update()
                scale_after = scaler.get_scale()
                if scale_after >= scale_before:
                    scheduler.step()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=grad_clip)
                optimizer.step()
                scheduler.step()
            current_step += 1
            train_batch_losses.append(loss.item())

            with torch.no_grad():
                valid = msk & torch.isfinite(preds) & torch.isfinite(tgt)
                if valid.any():
                    diff = preds[valid] - tgt[valid]
                    train_sq_err += torch.sum(diff**2).item()
                    train_abs_err += torch.sum(torch.abs(diff)).item()
                    train_pixel_count += valid.sum().item()

        # Compute train metrics
        valid_losses = [l for l in train_batch_losses if not math.isnan(l)]
        epoch_train_loss = float(np.mean(valid_losses)) if valid_losses else float("nan")
        epoch_train_rmse = math.sqrt(train_sq_err / train_pixel_count) if train_pixel_count > 0 else 0.0
        epoch_train_mae = (train_abs_err / train_pixel_count) if train_pixel_count > 0 else 0.0

        # Validation Pass
        model.depth_head.eval()
        val_batch_losses = []
        val_sq_err = 0.0
        val_abs_err = 0.0
        val_pixel_count = 0

        val_sq_err_tall = 0.0
        val_abs_err_tall = 0.0
        val_pixel_count_tall = 0

        with torch.no_grad():
            for v_batch in val_loader:
                v_img = v_batch["image"].to(device, non_blocking=True)
                v_tgt = v_batch["depth"].to(device, non_blocking=True)
                v_msk = v_batch["mask"].to(device, non_blocking=True)

                with torch.amp.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp):
                    v_feats = model.pretrained(v_img)
                    v_preds = model.depth_head(v_feats, 37, 37)

                v_loss = criterion(v_preds.float(), v_tgt.float(), v_msk)
                val_batch_losses.append(v_loss.item())

                valid = v_msk & torch.isfinite(v_preds) & torch.isfinite(v_tgt)
                if valid.any():
                    diff = v_preds[valid] - v_tgt[valid]
                    val_sq_err += torch.sum(diff**2).item()
                    val_abs_err += torch.sum(torch.abs(diff)).item()
                    val_pixel_count += valid.sum().item()

                # Tall structure band: GT >= 15.0 m
                valid_tall = valid & (v_tgt >= 15.0)
                if valid_tall.any():
                    diff_tall = v_preds[valid_tall] - v_tgt[valid_tall]
                    val_sq_err_tall += torch.sum(diff_tall**2).item()
                    val_abs_err_tall += torch.sum(torch.abs(diff_tall)).item()
                    val_pixel_count_tall += valid_tall.sum().item()

        valid_val_losses = [l for l in val_batch_losses if not math.isnan(l)]
        epoch_val_loss = float(np.mean(valid_val_losses)) if valid_val_losses else float("nan")
        epoch_val_rmse = math.sqrt(val_sq_err / val_pixel_count) if val_pixel_count > 0 else 0.0
        epoch_val_mae = (val_abs_err / val_pixel_count) if val_pixel_count > 0 else 0.0

        epoch_val_rmse_tall = math.sqrt(val_sq_err_tall / val_pixel_count_tall) if val_pixel_count_tall > 0 else 0.0
        epoch_val_mae_tall = (val_abs_err_tall / val_pixel_count_tall) if val_pixel_count_tall > 0 else 0.0

        current_lr = optimizer.param_groups[0]["lr"]
        epoch_sec = time.perf_counter() - epoch_t0
        total_elapsed_sec = prior_elapsed_sec + (time.perf_counter() - start_wall_time)
        peak_vram_mb = torch.cuda.max_memory_allocated() / (1024**2) if torch.cuda.is_available() else 0.0

        # Checkpoint logic
        saved_best = False
        saved_best_tall = False

        # Save last checkpoint every epoch
        torch.save(model.state_dict(), str(last_ckpt_path))

        if epoch_val_rmse < best_val_rmse:
            best_val_rmse = epoch_val_rmse
            best_epoch = epoch
            torch.save(model.state_dict(), str(best_ckpt_path))
            saved_best = True

        if epoch_val_rmse_tall < best_val_rmse_tall and epoch_val_rmse_tall > 0.0:
            best_val_rmse_tall = epoch_val_rmse_tall
            torch.save(model.state_dict(), str(best_tall_ckpt_path))
            saved_best_tall = True

        flags = []
        if saved_best:
            flags.append("[NEW BEST VAL]")
        if saved_best_tall:
            flags.append("[NEW BEST TALL]")
        flag_str = " " + " ".join(flags) if flags else ""

        # Terminal and File Logging
        logger.info(
            f"Epoch {epoch:02d}/{epochs:02d} | "
            f"Train Loss: {epoch_train_loss:.4f} | Train RMSE: {epoch_train_rmse:.3f}m | "
            f"Val Loss: {epoch_val_loss:.4f} | Val RMSE: {epoch_val_rmse:.3f}m | "
            f"Val Tall RMSE (>=15m): {epoch_val_rmse_tall:.3f}m | "
            f"LR: {current_lr:.6f} | Time: {epoch_sec:.1f}s{flag_str}"
        )

        # JSONL Logging
        metrics_record = {
            "epoch": epoch,
            "step": current_step,
            "train_loss": round(epoch_train_loss, 5) if not math.isnan(epoch_train_loss) else "nan",
            "train_rmse": round(epoch_train_rmse, 4),
            "train_mae": round(epoch_train_mae, 4),
            "val_loss": round(epoch_val_loss, 5) if not math.isnan(epoch_val_loss) else "nan",
            "val_rmse": round(epoch_val_rmse, 4),
            "val_mae": round(epoch_val_mae, 4),
            "val_rmse_tall": round(epoch_val_rmse_tall, 4),
            "val_mae_tall": round(epoch_val_mae_tall, 4),
            "val_tall_pixels": val_pixel_count_tall,
            "lr": round(current_lr, 8),
            "epoch_seconds": round(epoch_sec, 2),
            "elapsed_seconds": round(total_elapsed_sec, 2),
            "peak_vram_mb": round(peak_vram_mb, 1),
            "best_val_rmse": round(best_val_rmse, 4),
            "best_val_rmse_tall": round(best_val_rmse_tall, 4),
            "saved_best": saved_best,
            "saved_best_tall": saved_best_tall,
        }
        with open(jsonl_log, "a", encoding="utf-8") as f_jsonl:
            f_jsonl.write(json.dumps(metrics_record) + "\n")

        # CSV Logging
        with open(csv_log, "a", newline="", encoding="utf-8") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerow([
                epoch,
                current_step,
                round(epoch_train_loss, 5) if not math.isnan(epoch_train_loss) else "nan",
                round(epoch_train_rmse, 4),
                round(epoch_train_mae, 4),
                round(epoch_val_loss, 5) if not math.isnan(epoch_val_loss) else "nan",
                round(epoch_val_rmse, 4),
                round(epoch_val_mae, 4),
                round(epoch_val_rmse_tall, 4),
                round(epoch_val_mae_tall, 4),
                val_pixel_count_tall,
                round(current_lr, 8),
                round(epoch_sec, 2),
                round(total_elapsed_sec, 2),
                round(peak_vram_mb, 1),
            ])

        history["epochs"].append(epoch)
        history["train_loss"].append(epoch_train_loss)
        history["train_rmse"].append(epoch_train_rmse)
        history["val_loss"].append(epoch_val_loss)
        history["val_rmse"].append(epoch_val_rmse)
        history["val_rmse_tall"].append(epoch_val_rmse_tall)
        history["lr"].append(current_lr)

        # Update checkpoint_state.json after every epoch
        state_info = {
            "completed_epochs": epoch,
            "best_epoch": best_epoch,
            "best_val_rmse_m": round(best_val_rmse, 4),
            "best_tall_rmse_m": round(best_val_rmse_tall, 4),
            "train_rmse_epoch_m": round(epoch_train_rmse, 4),
            "val_rmse_epoch_m": round(epoch_val_rmse, 4),
            "saved_checkpoints": {
                "best": "models/v1.1.0/best.pt",
                "best_tall": "models/v1.1.0/best_tall.pt",
                "last": "models/v1.1.0/last.pt",
            },
            "logs": {
                "jsonl": "logs/v1.1.0/train_metrics.jsonl",
                "csv": "logs/v1.1.0/train_metrics.csv",
                "curves_plot": "docs/assets/v1.1.0_training_curves.png",
            },
            "status": "RUNNING" if epoch < epochs else "COMPLETED",
            "ready_for_evaluation": True,
        }
        with open(ckpt_dir / "checkpoint_state.json", "w", encoding="utf-8") as f_state:
            json.dump(state_info, f_state, indent=2)

        # Plot training curves continuously
        plot_curves(history, repo_root / "docs" / "assets" / "v1.1.0_training_curves.png")

    total_training_time = time.perf_counter() - start_wall_time
    logger.info(
        f"\nTraining completed in {total_training_time:.2f} s ({total_training_time / 60:.1f} min). "
        f"Best Val RMSE: {best_val_rmse:.3f} m, Best Tall RMSE: {best_val_rmse_tall:.3f} m"
    )
    logger.info(f"Checkpoints saved: last={last_ckpt_path}, best={best_ckpt_path}, best_tall={best_tall_ckpt_path}")

    # Plot training curves
    plot_curves(history, repo_root / "docs" / "assets" / "v1.1.0_training_curves.png")

    return {
        "best_val_rmse": best_val_rmse,
        "best_val_rmse_tall": best_val_rmse_tall,
        "total_training_seconds": total_training_time,
        "epochs_completed": epochs,
        "last_ckpt": str(last_ckpt_path),
        "best_ckpt": str(best_ckpt_path),
        "best_tall_ckpt": str(best_tall_ckpt_path),
    }


def plot_curves(history: Dict[str, List[float]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epochs = history["epochs"]
    if len(epochs) < 2:
        return

    plt.figure(figsize=(14, 5), dpi=150)

    # Subplot 1: Loss
    plt.subplot(1, 2, 1)
    plt.plot(epochs, history["train_loss"], marker="o", markersize=3, color="#2563eb", label="Train Loss (SiLog)")
    plt.plot(epochs, history["val_loss"], marker="s", markersize=3, color="#f59e0b", label="Val Loss (SiLog)")
    plt.title("Fine-Tuning Loss (DepthWizard v1.1.0)")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()

    # Subplot 2: RMSE (Overall and Tall Band)
    plt.subplot(1, 2, 2)
    plt.plot(epochs, history["train_rmse"], marker="o", markersize=3, color="#10b981", label="Train RMSE (All)")
    plt.plot(epochs, history["val_rmse"], marker="s", markersize=3, color="#6366f1", label="Val RMSE (All)")
    plt.plot(epochs, history["val_rmse_tall"], marker="^", markersize=3, color="#ef4444", label="Val RMSE (Tall >=15m)")
    plt.title("Elevation RMSE (Overall vs Tall >=15m)")
    plt.xlabel("Epoch")
    plt.ylabel("RMSE (metres)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()

    plt.tight_layout()
    plt.savefig(str(output_path))
    plt.close()
    print(f"Saved training curves to: {output_path}")


if __name__ == "__main__":
    args = parse_args()
    train_v110(args)
