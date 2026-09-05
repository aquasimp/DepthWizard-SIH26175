"""Elevation estimation metrics computation."""

from typing import Dict, Optional

import numpy as np


def compute_elevation_metrics(
    pred: np.ndarray,
    target: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, float]:
    """Compute Bias, MAE, RMSE, MedAE, RMSE_db, Pearson r, delta1, delta2_5."""
    if mask is None:
        valid = np.isfinite(pred) & np.isfinite(target)
    else:
        valid = mask & np.isfinite(pred) & np.isfinite(target)

    if not np.any(valid):
        return {
            "bias": 0.0,
            "mae": 0.0,
            "rmse": 0.0,
            "medae": 0.0,
            "rmse_db": 0.0,
            "pearson_r": 0.0,
            "delta1": 0.0,
            "delta2_5": 0.0,
            "valid_pixels": 0,
        }

    p = pred[valid].astype(np.float64)
    g = target[valid].astype(np.float64)
    diff = p - g
    abs_diff = np.abs(diff)

    bias = float(np.mean(diff))
    mae = float(np.mean(abs_diff))
    rmse = float(np.sqrt(np.mean(diff**2)))
    medae = float(np.median(abs_diff))
    rmse_db = float(np.sqrt(np.mean((diff - bias) ** 2)))

    std_p = float(np.std(p))
    std_g = float(np.std(g))
    if std_p > 1e-8 and std_g > 1e-8:
        cov = float(np.mean((p - np.mean(p)) * (g - np.mean(g))))
        pearson_r = float(cov / (std_p * std_g))
    else:
        pearson_r = 0.0

    delta1 = float(np.mean(abs_diff < 1.0))
    delta2_5 = float(np.mean(abs_diff < 2.5))

    return {
        "bias": bias,
        "mae": mae,
        "rmse": rmse,
        "medae": medae,
        "rmse_db": rmse_db,
        "pearson_r": pearson_r,
        "delta1": delta1,
        "delta2_5": delta2_5,
        "valid_pixels": int(np.sum(valid)),
    }
