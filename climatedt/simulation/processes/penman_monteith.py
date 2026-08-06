"""Phase 10 — FAO-56 Penman-Monteith reference evapotranspiration.

Replaces the temperature-only Hargreaves-Samani method with the full
FAO-56 Penman-Monteith equation (Allen et al., 1998, Eq. 6).

ET0 = (0.408 · Δ · (Rn − G) + γ · 900/(T+273) · u2 · (es − ea)) / (Δ + γ · (1 + 0.34 · u2))

Requires: Tmax, Tmin, humidity (RH or ea), wind speed at 2m, radiation (Rn or Rs).
When these inputs are unavailable, falls back to Hargreaves-Samani (Phase 7 default).

Reference: FAO Irrigation and Drainage Paper No. 56, Chapter 4.
"""

from __future__ import annotations

import math


def saturation_vapor_pressure(temp_c: float) -> float:
    """Saturation vapor pressure (kPa) at temperature temp_c (degC).

    FAO-56 Eq. 11: es = 0.6108 · exp(17.27 · T / (T + 237.3))
    """
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def actual_vapor_pressure_from_rh(es: float, rh_pct: float) -> float:
    """Actual vapor pressure from relative humidity. FAO-56 Eq. 17."""
    return es * rh_pct / 100.0


def vapor_pressure_deficit(es: float, ea: float) -> float:
    """Vapor pressure deficit (kPa)."""
    return es - ea


def slope_saturation_vapor_pressure(temp_c: float) -> float:
    """Slope of saturation vapor pressure curve (kPa/degC). FAO-56 Eq. 13."""
    es = saturation_vapor_pressure(temp_c)
    return 4098.0 * es / (temp_c + 237.3) ** 2


def psychrometric_constant(pressure_kpa: float) -> float:
    """Psychrometric constant (kPa/degC). FAO-56 Eq. 8.

    gamma = 0.000665 · P where P is atmospheric pressure in kPa.
    """
    return 0.000665 * pressure_kpa


def net_radiation(
    latitude_deg: float,
    jday: int,
    tmax_c: float,
    tmin_c: float,
    rh_mean_pct: float | None = None,
    rs_mj: float | None = None,
    pressure_kpa: float = 101.3,
) -> dict[str, float]:
    """Compute net radiation Rn (MJ/m2/day) following FAO-56 Ch. 3.

    Returns dict with keys: Rn, Rns, Rnl, Rs, Rso, Ra.
    If rs_mj (measured solar radiation) is not provided, uses
    Hargreaves radiation formula (FAO-56 Eq. 50).
    """
    # Extraterrestrial radiation Ra (FAO-56 Eq. 21)
    phi = math.radians(latitude_deg)
    declination = 0.409 * math.sin(2.0 * math.pi * jday / 365.0 - 1.39)
    cos_omega_s = -math.tan(phi) * math.tan(declination)
    cos_omega_s = max(-1.0, min(1.0, cos_omega_s))
    omega_s = math.acos(cos_omega_s)
    # distance factor
    dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * jday / 365.0)
    # Ra in MJ/m2/day
    Gsc = 0.0820  # solar constant MJ/m2/min
    Ra = (
        (24.0 * 60.0 / math.pi)
        * Gsc
        * dr
        * (
            omega_s * math.sin(phi) * math.sin(declination)
            + math.cos(phi) * math.cos(declination) * math.sin(omega_s)
        )
    )

    # Solar radiation Rs
    if rs_mj is not None:
        Rs = rs_mj
    else:
        # Hargreaves radiation formula (FAO-56 Eq. 50)
        Rs = 0.16 * math.sqrt(tmax_c - tmin_c) * Ra

    # Clear-sky radiation Rso (FAO-56 Eq. 36-37)
    Rso = (0.75 + 2e-5 * 0.0) * Ra  # elevation=0 simplified

    # Net shortwave Rns (FAO-56 Eq. 38)
    albedo = 0.23  # grass reference
    Rns = (1.0 - albedo) * Rs

    # Net longwave Rnl (FAO-56 Eq. 39)
    sigma = 4.903e-9  # Stefan-Boltzmann MJ/K4/m2/day
    tmin_k = tmin_c + 273.16
    tmax_k = tmax_c + 273.16
    # Actual vapor pressure — use RH if available, else estimate from Tmin (Eq. 48)
    if rh_mean_pct is not None:
        es_tmin = saturation_vapor_pressure(tmin_c)
        es_tmax = saturation_vapor_pressure(tmax_c)
        es_mean = (es_tmin + es_tmax) / 2.0
        ea = actual_vapor_pressure_from_rh(es_mean, rh_mean_pct)
    else:
        ea = saturation_vapor_pressure(tmin_c)  # approx as Tdew ~ Tmin

    Rnl = (
        sigma
        * ((tmax_k**4 + tmin_k**4) / 2.0)
        * (0.34 - 0.14 * math.sqrt(ea))
        * (1.35 * Rs / max(Rso, 0.01) - 0.35)
    )

    Rn = Rns - Rnl

    return {"Rn": Rn, "Rns": Rns, "Rnl": Rnl, "Rs": Rs, "Rso": Rso, "Ra": Ra}


def penman_monteith_et0(
    tmax_c: float,
    tmin_c: float,
    latitude_deg: float,
    jday: int,
    wind_speed_2m_ms: float = 2.0,
    rh_mean_pct: float | None = None,
    rs_mj: float | None = None,
    pressure_kpa: float = 101.3,
    elevation_m: float = 0.0,
) -> float:
    """FAO-56 Penman-Monteith reference ET0 (mm/day).

    Allen et al. (1998), FAO Irrigation and Drainage Paper No. 56, Eq. 6.

    Args:
        tmax_c: Daily maximum temperature (degC).
        tmin_c: Daily minimum temperature (degC).
        latitude_deg: Latitude in decimal degrees.
        jday: Day of year (1-366).
        wind_speed_2m_ms: Wind speed at 2m height (m/s). Default 2.0 m/s.
        rh_mean_pct: Mean daily relative humidity (%). Default None.
        rs_mj: Measured solar radiation (MJ/m2/day). Default None.
        pressure_kpa: Atmospheric pressure (kPa). Default 101.3 (sea level).
        elevation_m: Elevation above sea level (m). Used if pressure not given.

    Returns:
        Reference evapotranspiration ET0 in mm/day.

    Raises ValueError for non-physical inputs.
    """
    if tmax_c - tmin_c <= 0:
        raise ValueError("Tmax must exceed Tmin for Penman-Monteith")
    if not math.isfinite(tmax_c) or not math.isfinite(tmin_c):
        raise ValueError("Temperatures must be finite")

    # Mean temperature
    tmean_c = (tmax_c + tmin_c) / 2.0

    # Atmospheric pressure (FAO-56 Eq. 7) if not given
    if elevation_m > 0 and pressure_kpa == 101.3:
        pressure_kpa = 101.3 * ((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26

    # Slope of saturation vapor pressure curve (delta)
    delta = slope_saturation_vapor_pressure(tmean_c)

    # Saturation vapor pressure
    es_tmax = saturation_vapor_pressure(tmax_c)
    es_tmin = saturation_vapor_pressure(tmin_c)
    es = (es_tmax + es_tmin) / 2.0

    # Actual vapor pressure
    if rh_mean_pct is not None:
        ea = actual_vapor_pressure_from_rh(es, rh_mean_pct)
    else:
        ea = saturation_vapor_pressure(tmin_c)  # approximate dew point

    # Psychrometric constant
    gamma = psychrometric_constant(pressure_kpa)

    # Net radiation
    net_rad = net_radiation(latitude_deg, jday, tmax_c, tmin_c, rh_mean_pct, rs_mj, pressure_kpa)
    Rn = net_rad["Rn"]

    # Soil heat flux G (FAO-56 Eq. 45-46) — negligible for daily timestep
    G = 0.0

    # FAO-56 Penman-Monteith Eq. 6
    numerator = 0.408 * delta * (Rn - G) + gamma * (
        900.0 / (tmean_c + 273.0)
    ) * wind_speed_2m_ms * (es - ea)
    denominator = delta + gamma * (1.0 + 0.34 * wind_speed_2m_ms)

    return max(0.0, numerator / denominator)


def et0_auto(
    tmax_c: float,
    tmin_c: float,
    latitude_deg: float,
    jday: int,
    wind_speed_2m_ms: float | None = None,
    rh_mean_pct: float | None = None,
    rs_mj: float | None = None,
    pressure_kpa: float = 101.3,
) -> tuple[float, str]:
    """Auto-select ET0 method based on data availability.

    If humidity AND wind AND radiation are available: Penman-Monteith.
    Otherwise: Hargreaves-Samani (temperature-only fallback).

    Returns (et0_mm_per_day, method_name).
    """
    from climatedt.simulation.processes.evapotranspiration import hargreaves_et0

    if all(v is not None for v in [wind_speed_2m_ms, rh_mean_pct, rs_mj]):
        et0 = penman_monteith_et0(
            tmax_c,
            tmin_c,
            latitude_deg,
            jday,
            wind_speed_2m_ms=wind_speed_2m_ms,
            rh_mean_pct=rh_mean_pct,
            rs_mj=rs_mj,
            pressure_kpa=pressure_kpa,
        )
        return et0, "FAO56_PENMAN_MONTEITH"
    return hargreaves_et0(tmax_c, tmin_c, latitude_deg, jday), "HARGREAVES_SAMANI"
