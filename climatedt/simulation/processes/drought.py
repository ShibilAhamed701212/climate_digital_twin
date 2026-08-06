"""Phase 7 — Drought indices.

Standardized Precipitation-Evapotranspiration Index (SPEI), following
Vicente-Serrano et al. (2010).  D = P - PET is accumulated over a scale
(months); a 3-parameter log-logistic distribution is fitted to the
accumulated series by L-moments, and the resulting probability is mapped to
the standard normal distribution.  SPEI < 0 indicates drier-than-median
conditions.

Reference:
    Vicente-Serrano, S.M., Beguería, S., López-Moreno, J.I. (2010).
    "A Multiscalar Drought Index Sensitive to Global Warming: The
    Standardized Precipitation Evapotranspiration Index." J. Climate 23.
    Implementation follows the R `spei` package conventions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:
    from scipy.special import gamma as _gamma_fn
    from scipy.stats import norm as _norm
except ImportError:  # pragma: no cover - scipy is a project dependency
    _gamma_fn = None
    _norm = None


class SPEIResult:
    """SPEI output with method provenance metadata."""

    def __init__(
        self,
        values: list[float],
        method: str,
        scale: int,
        sample_count: int,
        fallback_used: bool = False,
        fallback_reason: str = "",
    ) -> None:
        self.values = values
        self.method = method
        self.scale = scale
        self.sample_count = sample_count
        self.fallback_used = fallback_used
        self.fallback_reason = fallback_reason


@dataclass(frozen=True)
class LogLogisticParams:
    """3-parameter log-logistic distribution (gamma, alpha, beta)."""

    gamma: float
    alpha: float
    beta: float

    def cdf(self, x: float) -> float:
        """F(x) = (1 + (alpha/(x-gamma))^beta)^-1 for x > gamma."""
        if x <= self.gamma:
            return 0.0
        return 1.0 / (1.0 + (self.alpha / (x - self.gamma)) ** self.beta)


def _pwms(x: list[float]) -> tuple[float, float, float]:
    """Probability weighted moments b0, b1, b2 (sorted ascending)."""
    xs = sorted(x)
    n = len(xs)
    b0 = sum(xs) / n
    if n < 2:
        return b0, 0.0, 0.0
    b1 = sum((i) * v for i, v in enumerate(xs)) / (n * (n - 1))
    if n < 3:
        return b0, b1, 0.0
    b2 = sum((i - 1) * i * v for i, v in enumerate(xs)) / (n * (n - 1) * (n - 2))
    return b0, b1, b2


def fit_loglogistic(x: list[float]) -> LogLogisticParams:
    """Fit the 3-parameter log-logistic by L-moments (SPEI method).

    L-skewness tau3 = L3/L2 determines beta = 1/tau3; scale and location
    then follow from L1, L2.  Raises ValueError when the series cannot be
    fitted (too short, zero spread, or tau3 outside the valid domain).
    """
    n = len(x)
    if n < 3:
        raise ValueError(f"Need at least 3 values to fit log-logistic, got {n}")
    b0, b1, b2 = _pwms(x)
    l1 = b0
    l2 = 2 * b1 - b0
    l3 = 6 * b2 - 6 * b1 + b0
    if abs(l2) < 1e-12:
        raise ValueError("Cannot fit log-logistic: zero L-scale (degenerate series)")
    tau3 = l3 / l2
    if not 0.0 < tau3 < 1.0:
        # tau3 must lie in (0,1) for a finite-mean log-logistic.
        raise ValueError(f"Cannot fit log-logistic: L-skewness {tau3:.4f} outside (0,1)")
    beta = 1.0 / tau3
    if beta <= 1.0:
        raise ValueError(f"Cannot fit log-logistic: beta={beta:.4f} <= 1 (no finite mean)")
    if _gamma_fn is None:  # pragma: no cover
        raise RuntimeError("scipy is required for SPEI")
    g = _gamma_fn(1.0 + 1.0 / beta) * _gamma_fn(1.0 - 1.0 / beta)
    alpha = l2 * beta / g
    gamma = l1 - alpha * g
    return LogLogisticParams(gamma=gamma, alpha=alpha, beta=beta)


def spei_from_monthly(
    d_values: list[float],
    scale: int = 3,
) -> list[float]:
    """Compute SPEI for a monthly D = P - PET series.
    Values only — for method provenance use spei_from_monthly_with_metadata."""
    result = spei_from_monthly_detailed(d_values, scale)
    return result.values


def spei_from_monthly_detailed(
    d_values: list[float],
    scale: int = 3,
) -> SPEIResult:
    """Compute SPEI with method provenance metadata.

    Args:
        d_values: Monthly P - PET (mm), chronological order.
        scale: Accumulation timescale in months (1, 3, 6, 12, ...).

    Returns:
        SPEI values for every month; the first (scale-1) entries are NaN
        because accumulation is not yet defined.

    Raises ValueError when the fitted distribution is degenerate for the
    accumulated series.
    """
    if scale < 1:
        raise ValueError(f"scale must be >= 1, got {scale}")
    if not d_values:
        return SPEIResult([], "INSUFFICIENT_DATA", scale, 0)

    n = len(d_values)
    accumulated: list[float] = []
    running = 0.0
    for i, d in enumerate(d_values):
        running += d
        if i >= scale:
            running -= d_values[i - scale]
        accumulated.append(running)

    fit_window = [v for v in accumulated[scale - 1 :] if math.isfinite(v)]
    if len(fit_window) < 30:
        mean = sum(fit_window) / len(fit_window) if fit_window else 0.0
        var = sum((v - mean) ** 2 for v in fit_window) / len(fit_window) if fit_window else 0.0
        sd = math.sqrt(var) if var > 0 else 1.0
        out: list[float] = []
        for i, v in enumerate(accumulated):
            if i < scale - 1:
                out.append(float("nan"))
            else:
                out.append((v - mean) / sd if sd > 0 else 0.0)
        return SPEIResult(
            out,
            "STANDARDIZED_ANOMALY",
            scale,
            len(fit_window),
            fallback_used=True,
            fallback_reason=f"Fit window too short: {len(fit_window)} < 30",
        )

    params = fit_loglogistic(fit_window)
    if _norm is None:  # pragma: no cover
        raise RuntimeError("scipy is required for SPEI")

    out = []
    for i, v in enumerate(accumulated):
        if i < scale - 1:
            out.append(float("nan"))
            continue
        p = params.cdf(v)
        p = max(1e-9, min(1.0 - 1e-9, p))
        out.append(float(_norm.ppf(p)))
    return SPEIResult(
        out,
        "SPEI_LMOMENT",
        scale,
        len(fit_window),
    )


def spei_classify(spei_value: float) -> str:
    """Map an SPEI value to a drought category (McKee et al. categories)."""
    if spei_value != spei_value:  # NaN
        return "UNKNOWN"
    if spei_value >= 2.0:
        return "EXTREME_WET"
    if spei_value >= 1.5:
        return "SEVERE_WET"
    if spei_value >= 1.0:
        return "MODERATE_WET"
    if spei_value >= -1.0:
        return "NEAR_NORMAL"
    if spei_value >= -1.5:
        return "MODERATE_DROUGHT"
    if spei_value >= -2.0:
        return "SEVERE_DROUGHT"
    return "EXTREME_DROUGHT"
