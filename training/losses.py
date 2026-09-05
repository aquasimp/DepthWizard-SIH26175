"""Loss functions for metric nDSM fine-tuning."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class MaskedSILogLoss(nn.Module):
    """Scale-Invariant Logarithmic Loss with lambda=0.85."""

    def __init__(self, lambd: float = 0.85, eps: float = 1e-6):
        super().__init__()
        self.lambd = lambd
        self.eps = eps

    def forward(self, pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        if not mask.any():
            return pred.new_tensor(0.0)

        p = pred[mask]
        t = target[mask]
        diff = torch.log(torch.clamp(p, min=self.eps)) - torch.log(torch.clamp(t, min=self.eps))
        loss = torch.mean(diff ** 2) - self.lambd * (torch.mean(diff) ** 2)
        return torch.sqrt(torch.clamp(loss, min=0.0))


class MultiScaleGradientLoss(nn.Module):
    """Multi-scale gradient matching loss over 4 scales with weights [1.0, 0.5, 0.25, 0.125]."""

    def __init__(self, weights=(1.0, 0.5, 0.25, 0.125)):
        super().__init__()
        self.weights = weights

    def forward(self, pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        total_loss = pred.new_tensor(0.0)
        curr_pred = pred
        curr_target = target
        curr_mask = mask.float()

        for w in self.weights:
            # Finite differences
            dx_p = torch.abs(curr_pred[:, :, :, :-1] - curr_pred[:, :, :, 1:])
            dx_t = torch.abs(curr_target[:, :, :, :-1] - curr_target[:, :, :, 1:])
            mask_x = curr_mask[:, :, :, :-1] * curr_mask[:, :, :, 1:]

            dy_p = torch.abs(curr_pred[:, :, :-1, :] - curr_pred[:, :, 1:, :])
            dy_t = torch.abs(curr_target[:, :, :-1, :] - curr_target[:, :, 1:, :])
            mask_y = curr_mask[:, :, :-1, :] * curr_mask[:, :, 1:, :]

            loss_x = (torch.abs(dx_p - dx_t) * mask_x).sum() / (mask_x.sum() + 1e-6)
            loss_y = (torch.abs(dy_p - dy_t) * mask_y).sum() / (mask_y.sum() + 1e-6)
            total_loss = total_loss + w * (loss_x + loss_y)

            # Downsample for next scale
            if w != self.weights[-1]:
                curr_pred = F.avg_pool2d(curr_pred, kernel_size=2, stride=2)
                curr_target = F.avg_pool2d(curr_target, kernel_size=2, stride=2)
                curr_mask = F.avg_pool2d(curr_mask, kernel_size=2, stride=2) > 0.5
                curr_mask = curr_mask.float()

        return total_loss


class CompositeDepthLoss(nn.Module):
    """Composite loss: SILog (lambda=0.85) + L1 + Multi-scale gradient loss."""

    def __init__(self, lambd: float = 0.85, l1_weight: float = 1.0, grad_weight: float = 0.5):
        super().__init__()
        self.silog = MaskedSILogLoss(lambd=lambd)
        self.grad_loss = MultiScaleGradientLoss()
        self.l1_weight = l1_weight
        self.grad_weight = grad_weight

    def forward(self, pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        silog = self.silog(pred, target, mask)
        l1 = (torch.abs(pred - target) * mask.float()).sum() / (mask.float().sum() + 1e-6)
        grad = self.grad_loss(pred, target, mask)
        return silog + self.l1_weight * l1 + self.grad_weight * grad
