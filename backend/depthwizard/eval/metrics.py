"""Elevation estimation accuracy metrics computation for remote-sensing terrain models."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def compute_elevation_metrics(
    pred: np.ndarray,
    target: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Compute comprehensive elevation accuracy metrics:

    Bias, MAE, MedAE, RMSE, RMSE_db (std), LE90, LE95, NMAD, Pearson r, delta1, delta2_5.

    Args:
        pred: Predicted elevation array (meters).
        target: Reference elevation array (meters).
        mask: Optional boolean mask of valid pixels.

    Returns:
        Dictionary of computed metric values.
    """
    if mask is None:
        valid = (
            np.isfinite(pred)
            & np.isfinite(target)
            & (pred != -9999.0)
            & (target != -9999.0)
        )
    else:
        valid = (
            mask
            & np.isfinite(pred)
            & np.isfinite(target)
            & (pred != -9999.0)
            & (target != -9999.0)
        )

    valid_count = int(np.sum(valid))
    if valid_count == 0:
        return {
            "bias": 0.0,
            "mae": 0.0,
            "medae": 0.0,
            "rmse": 0.0,
            "rmse_db": 0.0,
            "std_error": 0.0,
            "le90": 0.0,
            "le95": 0.0,
            "nmad": 0.0,
            "pearson_r": 0.0,
            "delta1": 0.0,
            "delta2_5": 0.0,
            "valid_pixels": 0,
            "total_pixels": int(pred.size),
        }

    p = pred[valid].astype(np.float64)
    g = target[valid].astype(np.float64)
    diff = p - g
    abs_diff = np.abs(diff)

    bias = float(np.mean(diff))
    mae = float(np.mean(abs_diff))
    medae = float(np.median(abs_diff))
    rmse = float(np.sqrt(np.mean(diff**2)))
    rmse_db = float(np.sqrt(np.mean((diff - bias) ** 2)))
    std_error = float(np.std(diff))

    # Standard photogrammetric accuracy metrics (LE90 & LE95)
    le90 = float(np.percentile(abs_diff, 90))
    le95 = float(np.percentile(abs_diff, 95))

    # Normalized Median Absolute Deviation (Höhle & Höhle, 2009)
    # Robust estimator of standard deviation resilient to blunders/outliers
    median_diff = np.median(diff)
    nmad = float(1.4826 * np.median(np.abs(diff - median_diff)))

    # Correlation coefficient
    std_p = float(np.std(p))
    std_g = float(np.std(g))
    if std_p > 1e-8 and std_g > 1e-8:
        cov = float(np.mean((p - np.mean(p)) * (g - np.mean(g))))
        pearson_r = float(np.clip(cov / (std_p * std_g), -1.0, 1.0))
    else:
        pearson_r = 0.0

    delta1 = float(np.mean(abs_diff < 1.0))
    delta2_5 = float(np.mean(abs_diff < 2.5))

    return {
        "bias": round(bias, 4),
        "mae": round(mae, 4),
        "medae": round(medae, 4),
        "rmse": round(rmse, 4),
        "rmse_db": round(rmse_db, 4),
        "std_error": round(std_error, 4),
        "le90": round(le90, 4),
        "le95": round(le95, 4),
        "nmad": round(nmad, 4),
        "pearson_r": round(pearson_r, 4),
        "delta1": round(delta1, 4),
        "delta2_5": round(delta2_5, 4),
        "valid_pixels": valid_count,
        "total_pixels": int(pred.size),
    }


def compute_error_histogram(
    diff: np.ndarray,
    num_bins: int = 50,
    range_m: Tuple[float, float] = (-15.0, 15.0),
) -> Dict[str, Any]:
    """Compute error distribution histogram for charting in UI and evaluation reports.

    Args:
        diff: Array of elevation differences (pred - ref) on valid pixels.
        num_bins: Number of histogram bins.
        range_m: Clipping min/max range in meters.

    Returns:
        Dict containing counts, bin_edges, bin_centers, and range.
    """
    valid_diff = diff[np.isfinite(diff)]
    if len(valid_diff) == 0:
        return {"counts": [], "bin_edges": [], "bin_centers": []}

    clipped = np.clip(valid_diff, range_m[0], range_m[1])
    counts, bin_edges = np.histogram(clipped, bins=num_bins, range=range_m)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    return {
        "counts": [int(c) for c in counts],
        "bin_edges": [round(float(e), 3) for e in bin_edges],
        "bin_centers": [round(float(c), 3) for c in bin_centers],
        "range_m": list(range_m),
    }
