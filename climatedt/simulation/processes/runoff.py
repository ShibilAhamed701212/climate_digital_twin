"""Phase 7 — Surface runoff via the USDA SCS Curve Number method (NRCS NEH-4).

    Q = (P - 0.2S)^2 / (P + 0.8S)    for P > 0.2S, else Q = 0
    S = 25400/CN - 254               (mm, metric SCS equation)

Antecedent Moisture Condition (AMC): the Curve Number is adjusted for the
5-day antecedent rainfall using the NEH-4 conversion formulas,

    CN_I   = CN_II / (2.281 - 0.01281 * CN_II)
    CN_III = CN_II / (0.427 + 0.00573 * CN_II)

AMC class thresholds are for the growing season (the SCS growing/dormant
split; the default here uses growing-season thresholds for the monsoon
region).  Q is a runoff *indicator* only — it is never interpreted as flood
depth or inundation.
"""

from __future__ import annotations

import math

# Growing-season antecedent rainfall (mm) AMC thresholds.
AMC_I_UPPER = 36.0  # < 36 mm -> AMC I (dry)
AMC_III_LOWER = 53.0  # > 53 mm -> AMC III (wet)


def _effective_cn(cn_ii: float, antecedent_5d_mm: float) -> float:
    """AMC-adjusted Curve Number from the 5-day antecedent rainfall (growing season)."""
    if antecedent_5d_mm <= AMC_I_UPPER:
        return cn_ii / (2.281 - 0.01281 * cn_ii)
    if antecedent_5d_mm >= AMC_III_LOWER:
        return cn_ii / (0.427 + 0.00573 * cn_ii)
    return cn_ii


def scs_runoff(
    rainfall_mm: float,
    cn_ii: float,
    antecedent_5d_mm: float = 0.0,
) -> float:
    """SCS-CN surface runoff Q (mm) for a single day.

    Args:
        rainfall_mm: Daily rainfall (mm).
        cn_ii: Curve Number for AMC II (normal) condition (0-100).
        antecedent_5d_mm: Sum of rainfall over the previous 5 days (mm).

    Raises ValueError for non-physical inputs.
    """
    if not math.isfinite(rainfall_mm) or rainfall_mm < 0:
        raise ValueError(f"rainfall_mm must be a non-negative finite number, got {rainfall_mm!r}")
    if not 0.0 <= cn_ii <= 100.0:
        raise ValueError(f"cn_ii must be in 0..100, got {cn_ii!r}")
    if not math.isfinite(antecedent_5d_mm) or antecedent_5d_mm < 0:
        raise ValueError(
            f"antecedent_5d_mm must be a non-negative finite number, got {antecedent_5d_mm!r}"
        )

    cn = _effective_cn(cn_ii, antecedent_5d_mm)
    s = 25400.0 / max(cn, 1e-9) - 254.0
    initial_abstraction = 0.2 * s
    if rainfall_mm <= initial_abstraction:
        return 0.0
    numerator = (rainfall_mm - initial_abstraction) ** 2
    denominator = rainfall_mm - initial_abstraction + s
    return max(0.0, numerator / denominator)
