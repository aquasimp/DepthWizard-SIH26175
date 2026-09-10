"""Loss functions for metric nDSM head fine-tuning.

Includes:
- Masked SILog (Scale-Invariant Logarithmic) loss (lambda=0.85, eps=1e-4)
- Masked L1 loss
- Multi-scale gradient matching loss (4 scales: 1x, 2x, 4x, 8x)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class MaskedSILogLoss(nn.Module):
    """Masked Scale-Invariant Logarithmic Loss."""

    def __init__(self, lambd: float = 0.85, eps: float = 1e-4):
        super().__init__()
        self.lambd = lambd
        self.eps = eps

    def forward(self, pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """Args:
        pred: (B, 1, H, W) or (B, H, W) float32 predicted metric height.
        target: (B, 1, H, W) or (B, H, W) float32 ground truth metric height.
        mask: (B, 1, H, W) or (B, H, W) bool valid pixel mask.
        """
        valid_mask = mask & (pred >= 0.0) & (target >= 0.0)
        if not valid_mask.any():
            return torch.tensor(0.0, device=pred.device, requires_grad=True)

        pred_valid = pred[valid_mask]
        target_valid = target[valid_mask]

        d = torch.log(pred_valid + self.eps) - torch.log(target_valid + self.eps)
        d_sq_mean = torch.mean(d**2)
        d_mean = torch.mean(d)

        # Var(d) with scale-invariance factor lambda
        loss_val = d_sq_mean - self.lambd * (d_mean**2)
        return torch.sqrt(torch.clamp(loss_val, min=1e-8))


class MaskedL1Loss(nn.Module):
    """Masked L1 Loss for metric elevation."""

    def forward(self, pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        valid_mask = mask & torch.isfinite(pred) & torch.isfinite(target)
        if not valid_mask.any():
            return torch.tensor(0.0, device=pred.device, requires_grad=True)

        return F.l1_loss(pred[valid_mask], target[valid_mask])


class MultiScaleGradientLoss(nn.Module):
    """Gradient matching loss across 4 scales (1x, 2x, 4x, 8x)."""

    def __init__(self, scales: int = 4):
        super().__init__()
        self.scales = scales

    def forward(self, pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        if pred.dim() == 3:
            pred = pred.unsqueeze(1)
        if target.dim() == 3:
            target = target.unsqueeze(1)
        if mask.dim() == 3:
            mask = mask.unsqueeze(1)

        total_grad_loss = torch.tensor(0.0, device=pred.device)
        diff = pred - target
        mask_float = mask.float()

        curr_diff = diff
        curr_mask = mask_float

        for scale in range(self.scales):
            if scale > 0:
                # Downsample by 2x using average pooling
                curr_diff = F.avg_pool2d(curr_diff, kernel_size=2, stride=2)
                curr_mask = F.avg_pool2d(curr_mask, kernel_size=2, stride=2)

            valid_m = curr_mask > 0.5

            # Gradients in x and y directions
            grad_x = curr_diff[:, :, :, 1:] - curr_diff[:, :, :, :-1]
            mask_x = valid_m[:, :, :, 1:] & valid_m[:, :, :, :-1]

            grad_y = curr_diff[:, :, 1:, :] - curr_diff[:, :, :-1, :]
            mask_y = valid_m[:, :, 1:, :] & valid_m[:, :, :-1, :]

            loss_x = (
                torch.mean(torch.abs(grad_x[mask_x]))
                if mask_x.any()
                else torch.tensor(0.0, device=pred.device)
            )
            loss_y = (
                torch.mean(torch.abs(grad_y[mask_y]))
                if mask_y.any()
                else torch.tensor(0.0, device=pred.device)
            )

            total_grad_loss = total_grad_loss + (loss_x + loss_y) / (2**scale)

        return total_grad_loss / self.scales


class MetricNDSMLoss(nn.Module):
    """Composite loss for metric nDSM head training:
    L_total = L_silog + 0.5 * L_l1 + 0.5 * L_grad
    """

    def __init__(self, lambd: float = 0.85, eps: float = 1e-4):
        super().__init__()
        self.silog = MaskedSILogLoss(lambd=lambd, eps=eps)
        self.l1 = MaskedL1Loss()
        self.grad = MultiScaleGradientLoss(scales=4)

    def forward(
        self,
        pred: torch.Tensor,
        target: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        l_silog = self.silog(pred, target, mask)
        l_l1 = self.l1(pred, target, mask)
        l_grad = self.grad(pred, target, mask)
        return l_silog + 0.5 * l_l1 + 0.5 * l_grad


# Alias for architectural naming convention
CompositeLoss = MetricNDSMLoss
