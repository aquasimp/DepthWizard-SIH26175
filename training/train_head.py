"""Fine-tuning script for Depth Anything V3 Small metric nDSM head on GAMUS dataset."""

import argparse
import csv
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend and repo_root are on sys.path
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
from depthwizard.utils.logging import logger
from torch.utils.data import DataLoader, Subset

from training.dataset import GAMUSDataset
from training.losses import MetricNDSMLoss


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune metric nDSM head on GAMUS dataset.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/dav3s_gamus_smoke.yaml",
        help="Path to YAML training configuration file.",
    )
    parser.add_argument("--epochs", type=int, default=None, help="Override number of epochs.")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate.")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size.")
    parser.add_argument("--device", type=str, default=None, help="Device to use ('cuda' or 'cpu').")
    parser.add_argument(
        "--resume", type=str, default=None, help="Path to checkpoint to resume from."
    )
    return parser.parse_args()


def load_config(config_path: Path) -> Dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)
    return config


def compute_metrics(
    pred: torch.Tensor,
    target: torch.Tensor,
    mask: torch.Tensor,
) -> Dict[str, float]:
    """Compute evaluation metrics: RMSE, MAE, AbsRel, delta1, delta2, delta3."""
    valid = mask & torch.isfinite(pred) & torch.isfinite(target)
    if not valid.any():
        return {
            "rmse": 0.0,
            "mae": 0.0,
            "abs_rel": 0.0,
            "delta1": 1.0,
            "delta2": 1.0,
            "delta3": 1.0,
        }

    p = pred[valid]
    t = target[valid]

    diff = p - t
    rmse = torch.sqrt(torch.mean(diff**2)).item()
    mae = torch.mean(torch.abs(diff)).item()

    # Relative metrics evaluated where target > 0.0 to prevent division by zero
    gt_pos = t > 1e-3
    if gt_pos.any():
        p_pos = torch.clamp(p[gt_pos], min=1e-3)
        t_pos = t[gt_pos]
        abs_rel = torch.mean(torch.abs(p_pos - t_pos) / t_pos).item()
        ratio = torch.max(p_pos / t_pos, t_pos / p_pos)
        delta1 = torch.mean((ratio < 1.25).float()).item()
        delta2 = torch.mean((ratio < 1.25**2).float()).item()
        delta3 = torch.mean((ratio < 1.25**3).float()).item()
    else:
        abs_rel = 0.0
        delta1, delta2, delta3 = 1.0, 1.0, 1.0

    return {
        "rmse": rmse,
        "mae": mae,
        "abs_rel": abs_rel,
        "delta1": delta1,
        "delta2": delta2,
        "delta3": delta3,
    }


def configure_trainable_parameters(
    model: DepthAnythingV3Small,
) -> Tuple[List[torch.nn.Parameter], int, int]:
    """Freeze encoder completely and enable gradients only on depth_head.

    Returns:
        trainable_params: List of depth_head parameter tensors.
        trainable_count: Total number of trainable scalar parameters (~2.7M).
        frozen_count: Total number of frozen encoder scalar parameters (~21.5M).
    """
    for param in model.pretrained.parameters():
        param.requires_grad = False
    model.pretrained.eval()

    for param in model.depth_head.parameters():
        param.requires_grad = True

    trainable_params = [p for p in model.depth_head.parameters() if p.requires_grad]
    trainable_count = sum(p.numel() for p in trainable_params)
    frozen_count = sum(p.numel() for p in model.pretrained.parameters() if not p.requires_grad)
    return trainable_params, trainable_count, frozen_count


def train_head(
    config_path: Path,
    override_epochs: Optional[int] = None,
    override_lr: Optional[float] = None,
    override_batch_size: Optional[int] = None,
    override_device: Optional[str] = None,
    resume_path: Optional[str] = None,
) -> float:
    t_start = time.perf_counter()
    config = load_config(config_path)

    # Resolve configuration parameters (supporting both flat and nested schemas)
    m_cfg = config.get("model", {})
    d_cfg = config.get("data", {})
    t_cfg = config.get("training", {})

    # Set random seed if provided
    seed = config.get("seed", 42)
    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # Resolve execution device
    cfg_device = override_device or t_cfg.get("device") or config.get("device")
    if cfg_device and cfg_device != "auto":
        device = cfg_device
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    device_desc = f"{device} ({torch.cuda.get_device_name(0)})" if device == "cuda" else device
    logger.info("Starting training run", extra={"device": device_desc, "config": str(config_path)})
    print(f"Executing training on: {device_desc}")

    # Hyperparameters
    epochs = override_epochs if override_epochs is not None else (
        t_cfg.get("epochs") or config.get("epochs") or 10
    )
    base_lr = override_lr if override_lr is not None else float(
        t_cfg.get("lr") or config.get("learning_rate") or config.get("lr") or 3e-4
    )
    min_lr = float(t_cfg.get("min_lr") or config.get("min_lr") or 1e-5)
    batch_size = override_batch_size if override_batch_size is not None else (
        d_cfg.get("batch_size") or config.get("batch_size") or 4
    )
    weight_decay = float(
        t_cfg.get("weight_decay") or config.get("weight_decay") or 1e-4
    )
    warmup_ratio = float(
        t_cfg.get("warmup_ratio") or config.get("warmup_ratio") or 0.05
    )
    grad_clip = float(
        t_cfg.get("grad_clip") or config.get("grad_clip") or 1.0
    )
    use_amp = bool(
        t_cfg.get("amp") or config.get("amp") or False
    ) and (device == "cuda")

    run_name = config.get("run_name", config_path.stem)
    checkpoint_interval_steps = int(
        t_cfg.get("checkpoint_interval_steps") or config.get("checkpoint_interval_steps") or 25
    )

    # Output checkpoint resolution
    output_checkpoint_str = (
        t_cfg.get("output_checkpoint")
        or config.get("output_checkpoint")
    )
    if not output_checkpoint_str:
        out_dir = config.get("output_dir", "models/checkpoints")
        output_checkpoint_str = f"{out_dir}/dav3s_smoke.pth"
    output_checkpoint = Path(output_checkpoint_str)
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load model with strictly frozen encoder
    init_checkpoint = (
        resume_path
        or m_cfg.get("checkpoint")
        or config.get("checkpoint")
        or ("models/depth_anything_v3_vits.pth" if Path("models/depth_anything_v3_vits.pth").exists() else "models/depth_anything_v2_vits.pth")
    )
    model: DepthAnythingV3Small = load_dav3_small(init_checkpoint, device=device)

    # Scale output convolution weights if starting from raw base relative model
    if "depth_anything_v3_vits.pth" in str(init_checkpoint) or "depth_anything_v2_vits.pth" in str(init_checkpoint):
        model.depth_head.scratch.output_conv2[2].weight.data *= 58.0
        model.depth_head.scratch.output_conv2[2].bias.data *= 58.0

    # Freeze encoder and configure depth_head gradients
    trainable_params, trainable_count, frozen_count = configure_trainable_parameters(model)
    logger.info(
        "Model configured",
        extra={
            "trainable_parameters": trainable_count,
            "frozen_parameters": frozen_count,
        },
    )

    # 2. Datasets & Loaders
    manifest_str = d_cfg.get("manifest") or config.get("manifest")
    if not manifest_str:
        if "smoke" in str(config_path) or "smoke" in run_name:
            manifest_str = "data/gamus/smoke_manifest.csv"
        else:
            manifest_str = "data/gamus/manifest.csv"
    manifest_path = Path(manifest_str)

    crop_size = d_cfg.get("crop_size") or config.get("crop_size") or 518
    augment = bool(d_cfg.get("augment") or config.get("augment") or False)
    max_train_samples = (
        d_cfg.get("max_samples")
        or config.get("max_tiles")
        or config.get("max_train_tiles")
        or None
    )

    train_dataset = GAMUSDataset(
        manifest_path=manifest_path,
        split="train",
        crop_size=crop_size,
        augment=augment,
    )
    if max_train_samples and max_train_samples < len(train_dataset):
        train_dataset = Subset(train_dataset, list(range(max_train_samples)))

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=(device == "cuda"),
    )

    # Validation set (if available in manifest)
    val_dataset = GAMUSDataset(
        manifest_path=manifest_path,
        split="val",
        crop_size=crop_size,
        augment=False,
    )
    has_val = len(val_dataset) > 0
    val_loader = (
        DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=(device == "cuda"),
        )
        if has_val
        else None
    )

    print(f"Data ready: {len(train_dataset)} train samples ({len(train_loader)} batches/epoch), "
          f"{len(val_dataset)} val samples.")

    # 3. Loss, Optimizer, LR Scheduler
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
        min_ratio = min_lr / base_lr if base_lr > 0 else 0.01
        return min_ratio + (1.0 - min_ratio) * decay

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    # 4. Metrics Logging Setup
    log_dir = repo_root / "training" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_csv = log_dir / f"{run_name}_metrics.csv"
    with open(log_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "epoch",
            "train_loss",
            "train_rmse",
            "train_mae",
            "val_loss",
            "val_rmse",
            "val_mae",
            "lr",
            "step",
            "elapsed_seconds",
        ])

    epoch_train_losses: List[float] = []
    epoch_train_rmses: List[float] = []
    epoch_val_losses: List[float] = []
    epoch_val_rmses: List[float] = []

    best_val_rmse = float("inf")
    best_train_rmse = float("inf")
    current_step = 0

    # 5. Training & Validation Loop
    for epoch in range(1, epochs + 1):
        model.depth_head.train()
        model.pretrained.eval()  # Strictly freeze encoder

        batch_losses: List[float] = []
        batch_rmses: List[float] = []
        batch_maes: List[float] = []

        for batch in train_loader:
            images = batch["image"].to(device)
            targets = batch["depth"].to(device)
            masks = batch["mask"].to(device)

            optimizer.zero_grad()

            with torch.amp.autocast(device_type="cuda", enabled=use_amp):
                with torch.no_grad():
                    features = model.pretrained(images)

                h, w = images.shape[-2:]
                patch_h, patch_w = h // 14, w // 14
                preds = model.depth_head(features, patch_h, patch_w)
                loss = criterion(preds, targets, masks)

            if use_amp:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=grad_clip)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=grad_clip)
                optimizer.step()

            scheduler.step()

            batch_losses.append(loss.item())
            with torch.no_grad():
                metrics = compute_metrics(preds, targets, masks)
                batch_rmses.append(metrics["rmse"])
                batch_maes.append(metrics["mae"])

            current_step += 1

            if current_step % checkpoint_interval_steps == 0:
                torch.save(model.state_dict(), str(output_checkpoint))
                logger.info(
                    f"Saved interval checkpoint at step {current_step} to {output_checkpoint}"
                )

        train_loss = float(np.mean(batch_losses))
        train_rmse = float(np.mean(batch_rmses))
        train_mae = float(np.mean(batch_maes))
        epoch_train_losses.append(train_loss)
        epoch_train_rmses.append(train_rmse)

        # Validation evaluation
        val_loss: Optional[float] = None
        val_rmse: Optional[float] = None
        val_mae: Optional[float] = None

        if val_loader is not None:
            model.depth_head.eval()
            v_losses: List[float] = []
            v_rmses: List[float] = []
            v_maes: List[float] = []
            with torch.no_grad():
                for v_batch in val_loader:
                    v_images = v_batch["image"].to(device)
                    v_targets = v_batch["depth"].to(device)
                    v_masks = v_batch["mask"].to(device)

                    with torch.amp.autocast(device_type="cuda", enabled=use_amp):
                        v_features = model.pretrained(v_images)
                        vh, vw = v_images.shape[-2:]
                        v_preds = model.depth_head(v_features, vh // 14, vw // 14)
                        v_l = criterion(v_preds, v_targets, v_masks)

                    v_m = compute_metrics(v_preds, v_targets, v_masks)
                    v_losses.append(v_l.item())
                    v_rmses.append(v_m["rmse"])
                    v_maes.append(v_m["mae"])

            val_loss = float(np.mean(v_losses))
            val_rmse = float(np.mean(v_rmses))
            val_mae = float(np.mean(v_maes))
            epoch_val_losses.append(val_loss)
            epoch_val_rmses.append(val_rmse)

        current_lr = optimizer.param_groups[0]["lr"]
        elapsed_sec = time.perf_counter() - t_start

        # Append to CSV log
        with open(log_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                epoch,
                round(train_loss, 4),
                round(train_rmse, 4),
                round(train_mae, 4),
                round(val_loss, 4) if val_loss is not None else "",
                round(val_rmse, 4) if val_rmse is not None else "",
                round(val_mae, 4) if val_mae is not None else "",
                round(current_lr, 7),
                current_step,
                round(elapsed_sec, 2),
            ])

        # Logging to terminal
        val_str = f" | Val Loss: {val_loss:.4f} | Val RMSE: {val_rmse:.3f}m" if val_rmse is not None else ""
        print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} | Train RMSE: {train_rmse:.3f}m{val_str} | LR: {current_lr:.6f}")

        # Checkpoint selection
        is_best = False
        if val_rmse is not None:
            if val_rmse < best_val_rmse:
                best_val_rmse = val_rmse
                is_best = True
        else:
            if train_rmse < best_train_rmse:
                best_train_rmse = train_rmse
                is_best = True

        if is_best or epoch == epochs:
            torch.save(model.state_dict(), str(output_checkpoint))
            logger.info(
                f"Saved best model checkpoint to {output_checkpoint} (epoch {epoch})",
                extra={"epoch": epoch, "rmse_m": round(val_rmse if val_rmse is not None else train_rmse, 3)},
            )

    total_time = time.perf_counter() - t_start
    print(f"\nTraining completed in {total_time:.2f} s. Checkpoint saved to: {output_checkpoint}")
    print(f"Per-epoch log written to: {log_csv}")

    # 6. Plot and save training curves
    plot_path = Path("docs/assets/training_loss.png")
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(10, 4.5), dpi=150)

    plt.subplot(1, 2, 1)
    plt.plot(range(1, epochs + 1), epoch_train_losses, marker="o", markersize=3, color="#3b82f6", label="Train Loss")
    if epoch_val_losses:
        plt.plot(range(1, epochs + 1), epoch_val_losses, marker="x", markersize=3, color="#f59e0b", label="Val Loss")
    plt.title("Fine-Tuning Loss")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(range(1, epochs + 1), epoch_train_rmses, marker="s", markersize=3, color="#10b981", label="Train RMSE (m)")
    if epoch_val_rmses:
        plt.plot(range(1, epochs + 1), epoch_val_rmses, marker="^", markersize=3, color="#ef4444", label="Val RMSE (m)")
    plt.title("Elevation RMSE (metres)")
    plt.xlabel("Epoch")
    plt.ylabel("RMSE (m)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()

    plt.tight_layout()
    plt.savefig(str(plot_path))
    plt.close()
    logger.info(f"Saved training curves to {plot_path}")

    final_rmse = epoch_val_rmses[-1] if epoch_val_rmses else epoch_train_rmses[-1]
    return final_rmse


if __name__ == "__main__":
    args = parse_args()
    final_rmse = train_head(
        config_path=Path(args.config),
        override_epochs=args.epochs,
        override_lr=args.lr,
        override_batch_size=args.batch_size,
        override_device=args.device,
        resume_path=args.resume,
    )
    print(f"Final metric RMSE: {final_rmse:.3f} m")
    if "smoke" in args.config:
        assert final_rmse < 1.0, f"Smoke test train RMSE must be < 1.0 m, got {final_rmse:.3f} m"
        print("Smoke test assertion passed: train RMSE < 1.0 m.")
