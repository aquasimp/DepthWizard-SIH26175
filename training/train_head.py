"""Fine-tuning script for Depth Anything V2 Small metric nDSM head on GAMUS dataset."""

import argparse
import math
import sys
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
from depthwizard.depth.backbone import DepthAnythingV2Small, load_dav2_small
from depthwizard.utils.logging import logger
from torch.utils.data import DataLoader, Subset

from training.dataset import GAMUSDataset
from training.losses import MetricNDSMLoss


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune metric nDSM head on GAMUS dataset.")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/dav2s_gamus_smoke.yaml",
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
    model: DepthAnythingV2Small,
) -> Tuple[List[torch.nn.Parameter], int, int]:
    """Freeze encoder completely and enable gradients only on depth_head.

    Returns:
        trainable_params: List of depth_head parameter tensors.
        trainable_count: Total number of trainable scalar parameters (~3.2M).
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
    config = load_config(config_path)

    # Resolve device
    if override_device:
        device = override_device
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    logger.info("Starting training run", extra={"device": device, "config": str(config_path)})

    # Parameters
    m_cfg = config.get("model", {})
    d_cfg = config.get("data", {})
    t_cfg = config.get("training", {})

    epochs = override_epochs if override_epochs is not None else t_cfg.get("epochs", 10)
    base_lr = override_lr if override_lr is not None else float(t_cfg.get("lr", 5e-4))
    batch_size = (
        override_batch_size if override_batch_size is not None else d_cfg.get("batch_size", 2)
    )
    weight_decay = float(t_cfg.get("weight_decay", 1e-4))
    warmup_ratio = float(t_cfg.get("warmup_ratio", 0.05))
    output_checkpoint = Path(t_cfg.get("output_checkpoint", "models/dav2s_gamus_ft_v1.pth"))
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load model with frozen encoder
    init_checkpoint = resume_path or m_cfg.get("checkpoint", "models/depth_anything_v2_vits.pth")
    model: DepthAnythingV2Small = load_dav2_small(init_checkpoint, device=device)

    # Initialize output convolution weights to metric scale if starting from base relative model
    if "depth_anything_v2_vits.pth" in str(init_checkpoint):
        # Base model outputs relative depth (~0.28). Scale output layer to metric range (~15-20m).
        model.depth_head.scratch.output_conv2[2].weight.data *= 58.0
        model.depth_head.scratch.output_conv2[2].bias.data *= 58.0

    # Freeze encoder and enable depth_head gradients
    trainable_params, trainable_count, frozen_count = configure_trainable_parameters(model)
    logger.info(
        "Model configured",
        extra={
            "trainable_parameters": trainable_count,
            "frozen_parameters": frozen_count,
        },
    )

    # 2. Dataset & DataLoader
    manifest_path = Path(d_cfg.get("manifest", "data/gamus/manifest.csv"))
    crop_size = d_cfg.get("crop_size", 518)
    augment = d_cfg.get("augment", False)
    max_samples = d_cfg.get("max_samples", None)

    dataset = GAMUSDataset(
        manifest_path=manifest_path,
        split="train",
        crop_size=crop_size,
        augment=augment,
    )
    if max_samples and max_samples < len(dataset):
        indices = list(range(max_samples))
        dataset_to_use = Subset(dataset, indices)
    else:
        dataset_to_use = dataset

    loader = DataLoader(
        dataset_to_use,
        batch_size=batch_size,
        shuffle=True,
        num_workers=d_cfg.get("num_workers", 0),
        pin_memory=(device == "cuda"),
    )

    # 3. Loss & Optimizer
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

    total_steps = epochs * len(loader)
    warmup_steps = max(1, int(warmup_ratio * total_steps))

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lr_lambda)

    # 4. Training Loop
    epoch_losses: List[float] = []
    epoch_rmses: List[float] = []

    best_rmse = float("inf")
    current_step = 0

    for epoch in range(1, epochs + 1):
        model.depth_head.train()
        model.pretrained.eval()  # Keep encoder batchnorm/dropout frozen

        batch_losses: List[float] = []
        batch_rmses: List[float] = []

        for batch in loader:
            images = batch["image"].to(device)
            targets = batch["depth"].to(device)
            masks = batch["mask"].to(device)

            optimizer.zero_grad()

            with torch.no_grad():
                features = model.pretrained(images)

            h, w = images.shape[-2:]
            patch_h, patch_w = h // 14, w // 14
            preds = model.depth_head(features, patch_h, patch_w)

            loss = criterion(preds, targets, masks)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=1.0)
            optimizer.step()
            scheduler.step()

            batch_losses.append(loss.item())

            with torch.no_grad():
                metrics = compute_metrics(preds, targets, masks)
                batch_rmses.append(metrics["rmse"])

            current_step += 1

        mean_loss = float(np.mean(batch_losses))
        mean_rmse = float(np.mean(batch_rmses))
        epoch_losses.append(mean_loss)
        epoch_rmses.append(mean_rmse)

        logger.info(
            f"Epoch {epoch}/{epochs} | Loss: {mean_loss:.4f} | RMSE: {mean_rmse:.3f}m | LR: {optimizer.param_groups[0]['lr']:.6f}",
            extra={
                "epoch": epoch,
                "loss": round(mean_loss, 4),
                "rmse_m": round(mean_rmse, 3),
                "lr": round(optimizer.param_groups[0]["lr"], 6),
            },
        )

        # Save checkpoint if best RMSE
        if mean_rmse < best_rmse or epoch == epochs:
            best_rmse = min(best_rmse, mean_rmse)
            torch.save(model.state_dict(), str(output_checkpoint))
            logger.info(
                f"Saved checkpoint to {output_checkpoint}",
                extra={"epoch": epoch, "rmse_m": round(mean_rmse, 3)},
            )

    # 5. Generate and save training loss plot
    plot_path = Path("docs/assets/training_loss.png")
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, 4.5), dpi=150)
    plt.subplot(1, 2, 1)
    plt.plot(range(1, epochs + 1), epoch_losses, marker="o", color="#3b82f6", label="Train Loss")
    plt.title("Fine-Tuning Loss (SILog + L1 + Grad)")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(range(1, epochs + 1), epoch_rmses, marker="s", color="#10b981", label="Train RMSE (m)")
    plt.title("Elevation RMSE (metres)")
    plt.xlabel("Epoch")
    plt.ylabel("RMSE (m)")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()

    plt.tight_layout()
    plt.savefig(str(plot_path))
    plt.close()
    logger.info(f"Saved training curves to {plot_path}")

    # Check loss decrease
    if len(epoch_losses) >= 2:
        assert epoch_losses[-1] < epoch_losses[0], (
            f"Training loss did not decrease: epoch 1 = {epoch_losses[0]}, epoch {epochs} = {epoch_losses[-1]}"
        )

    final_rmse = epoch_rmses[-1]
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
    print(f"Training completed successfully. Final train RMSE: {final_rmse:.3f} m")
    if "smoke" in args.config:
        assert final_rmse < 1.0, f"Smoke test train RMSE must be < 1.0 m, got {final_rmse:.3f} m"
        print("Smoke test assertion passed: train RMSE < 1.0 m.")
