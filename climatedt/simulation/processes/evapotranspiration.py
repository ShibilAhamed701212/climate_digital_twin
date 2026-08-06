"""Phase 7 — Reference evapotranspiration (ET0).

Method: Hargreaves-Samani (HS), the FAO-56 temperature-based method.
Chosen because the available historical record contains only Tmax, Tmin and
Rainfall — FAO-56 Penman-Monteith requires humidity, wind and radiation which
we do not possess.  HS is the FAO-recommended alternative when those inputs
are missing (FAO-56 Chapter 4).

    ET0 = krs * (Tmean + 17.8) * (Tmax - Tmin)^0.5 * Ra

where ET0 and Ra are expressed as equivalent water depth (mm/day) and krs is
the calibration coefficient (0.0023 for interior regions, 0.0019 for coastal).
Ra is the extraterrestrial radiation, converted from MJ/m2/day to mm/day
using the factor 0.408 (FAO-56 Eq 21 + 1/lambda).

Reference case (FAO-56 Example 20): latitude 45.72 N, jday 196, Tmax 26.6 C,
Tmin 14.8 C, Ra = 40.55 MJ/m2/day -> ET0 = 5.03 mm/day.
"""

from __future__ import annotations

import math

# FAO-56 constants.
SOLAR_CONSTANT = 0.0820  # MJ m-2 min-1 (Gsc)
J_TO_MM = 0.408  # mm/day per MJ/m2/day (1/lambda, lambda ~2.45 MJ/kg)
DEFAULT_KRS = 0.0023  # interior region; coastal regions use 0.0019


def extraterrestrial_radiation(jday: int, latitude_deg: float) -> float:
    """FAO-56 Eq 21 — extraterrestrial radiation Ra in MJ/m2/day.

    Args:
        jday: Day of the year (1-366).
        latitude_deg: Latitude in decimal degrees (positive = north).
    """
    if not 1 <= jday <= 366:
        raise ValueError(f"jday must be in 1..366, got {jday}")
    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError(f"latitude_deg must be in -90..90, got {latitude_deg}")

    phi = math.radians(latitude_deg)
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * jday / 365.0)
    declination = 0.409 * math.sin(2.0 * math.pi * jday / 365.0 - 1.39)
    cos_omega = -math.tan(phi) * math.tan(declination)
    cos_omega = max(-1.0, min(1.0, cos_omega))
    omega_s = math.acos(cos_omega)

    ra = (
        (24.0 * 60.0 / math.pi)
        * SOLAR_CONSTANT
        * dr
        * (
            omega_s * math.sin(phi) * math.sin(declination)
            + math.cos(phi) * math.cos(declination) * math.sin(omega_s)
        )
    )
    return max(0.0, ra)


def hargreaves_et0(
    tmax_c: float,
    tmin_c: float,
    latitude_deg: float,
    jday: int,
    krs: float = DEFAULT_KRS,
) -> float:
    """Hargreaves-Samani reference evapotranspiration in mm/day.

    Raises ValueError for non-physical inputs (Tmin > Tmax, Tmax <= Tmin,
    non-finite values).
    """
    if not math.isfinite(tmax_c) or not math.isfinite(tmin_c):
        raise ValueError(f"tmax/tmin must be finite, got {tmax_c!r}/{tmin_c!r}")
    if tmin_c > tmax_c:
        raise ValueError(f"tmin ({tmin_c}) must not exceed tmax ({tmax_c})")
    if tmax_c - tmin_c <= 0:
        raise ValueError(f"tmax must exceed tmin, got {tmax_c!r}/{tmin_c!r}")
    if krs <= 0 or not math.isfinite(krs):
        raise ValueError(f"krs must be a positive finite number, got {krs!r}")

    tmean = (tmax_c + tmin_c) / 2.0
    ra_mj = extraterrestrial_radiation(jday, latitude_deg)
    ra_mm = ra_mj * J_TO_MM
    return krs * (tmean + 17.8) * (tmax_c - tmin_c) ** 0.5 * ra_mm
