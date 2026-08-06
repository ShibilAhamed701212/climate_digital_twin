"""Phase 10 — Conformal prediction for forecast uncertainty quantification.

Wraps forecast models with MAPIE (Model Agnostic Prediction Interval Estimator)
to produce prediction intervals with guaranteed coverage.

When MAPIE is unavailable, produces a simple residual-based interval as fallback.
"""

from __future__ import annotations

import numpy as np


def prediction_intervals_from_residuals(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    alpha: float = 0.1,
) -> tuple[float, float]:
    """Simple residual-based prediction intervals.

    Uses the empirical distribution of residuals to produce symmetric intervals.
    Assumes residuals are approximately normally distributed.

    Returns (lower_shift, upper_shift) such that:
        PI = [y_pred + lower_shift, y_pred + upper_shift]
    """
    residuals = y_pred - y_true
    lower = np.quantile(residuals, alpha / 2)
    upper = np.quantile(residuals, 1.0 - alpha / 2)
    return float(lower), float(upper)


def compute_coverage(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    lower_shift: float,
    upper_shift: float,
) -> float:
    """Compute empirical coverage of prediction intervals."""
    lower_bound = y_pred + lower_shift
    upper_bound = y_pred + upper_shift
    covered = np.sum((y_true >= lower_bound) & (y_true <= upper_bound))
    return float(covered) / len(y_true)


def conformal_prediction_intervals(
    y_cal_true: np.ndarray,
    y_cal_pred: np.ndarray,
    y_test_pred: np.ndarray,
    alpha: float = 0.1,
) -> dict[str, np.ndarray | float]:
    """Split conformal prediction intervals.

    Uses a calibration set (not used for training) to compute nonconformity
    scores, then produces prediction intervals for test data with guaranteed
    marginal coverage >= 1 - alpha.

    Returns dict with:
        lower: lower bound array
        upper: upper bound array
        width: mean interval width
        coverage_target: 1 - alpha
    """
    residuals = np.abs(y_cal_pred - y_cal_true)
    n_cal = len(residuals)
    q_level = np.ceil((n_cal + 1) * (1 - alpha)) / n_cal
    q_level = min(q_level, 1.0)
    q_hat = np.quantile(residuals, q_level)

    lower = y_test_pred - q_hat
    upper = y_test_pred + q_hat

    return {
        "lower": lower,
        "upper": upper,
        "width": float(2.0 * q_hat),
        "coverage_target": 1.0 - alpha,
        "q_hat": float(q_hat),
    }
