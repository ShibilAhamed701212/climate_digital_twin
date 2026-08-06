"""Phase 14B — Spatial operations for the Digital Twin grid.

Spatial interpolation, grid-wide hazard maps, and batch forecasting.
"""

from __future__ import annotations

import numpy as np
import xarray as xr



def nearest_neighbor(ds: xr.Dataset, target_lat: float, target_lon: float) -> dict:
    """Find nearest grid cell by Euclidean distance in lat/lon space."""
    lat_idx = int(np.abs(ds.latitude - target_lat).argmin())
    lon_idx = int(np.abs(ds.longitude - target_lon).argmin())
    return ds.grid_twin.cell_state(lat_idx, lon_idx)


def inverse_distance_weighted(
    ds: xr.Dataset,
    target_lat: float,
    target_lon: float,
    variable: str = "temperature_2m",
    power: int = 2,
    min_neighbors: int = 4,
) -> dict:
    """IDW interpolation for a scalar variable."""
    time_idx = -1
    lats = ds.latitude.values
    lons = ds.longitude.values

    distances = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            d = np.sqrt((lat - target_lat) ** 2 + (lon - target_lon) ** 2)
            if d < 1e-6:
                d = 1e-6
            distances.append((d, i, j))

    distances.sort()
    neighbors = distances[:min_neighbors]

    # Get values (handle both DataArray and named accessors)
    if variable == "temperature_2m":
        values = ds.t2m.isel(valid_time=time_idx) - 273.15
    elif variable == "wind_speed_ms":
        u = ds.u10.isel(valid_time=time_idx)
        v = ds.v10.isel(valid_time=time_idx)
        values = np.sqrt(u**2 + v**2)
    elif variable == "pressure_hpa":
        values = ds.sp.isel(valid_time=time_idx) / 100.0
    else:
        values = ds[variable].isel(valid_time=time_idx)

    weights = 1.0 / np.array([d[0] ** power for d in neighbors])
    weights /= weights.sum()
    interpolated = sum(
        weights[k] * float(values[neighbors[k][1], neighbors[k][2]]) for k in range(min_neighbors)
    )
    return {
        "value": round(interpolated, 2),
        "method": f"IDW_p{power}_n{min_neighbors}",
        "source_cells": [
            {"lat": float(lats[neighbors[k][1]]), "lon": float(lons[neighbors[k][2]])}
            for k in range(min_neighbors)
        ],
        "weights": [round(w, 3) for w in weights.tolist()],
    }


def generate_hazard_map(ds: xr.Dataset, time_idx: int = -1) -> dict:
    """Run hazard evaluation across all grid cells.

    Returns a dict with per-cell hazard scores and a regional summary.
    Uses persistence-based forecast (yesterday = today).
    """
    from risk.evaluation.hazard_evaluator import HazardEvaluator
    from risk.evaluation.twin_adapter import TwinInputs

    evaluator = HazardEvaluator()

    lats = ds.latitude.values
    lons = ds.longitude.values
    time_dim = len(ds.valid_time)

    # Use second-to-last timestep as "today" for persistence
    t_idx = min(time_idx, time_dim - 2)
    prev_idx = max(t_idx - 1, 0) if time_dim > 1 else t_idx

    cells_total = len(lats) * len(lons)
    heat_map: list[dict] = []
    rain_map: list[dict] = []
    dry_map: list[dict] = []

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            cell = ds.grid_twin.cell_state(i, j, t_idx)
            prev = ds.grid_twin.cell_state(i, j, prev_idx) if time_dim > 1 else cell

            ti = TwinInputs(
                max_temp=cell["temperature_2m"],
                min_temp=prev.get("temperature_2m", cell["temperature_2m"]),
                rainfall=0.0,
                consecutive_hot_days=0,
                dry_period_days=0,
                multi_day_accumulation=None,
                seasonal_anomaly=0.0,
                forecast_uncertainty=0.0,
                twin_version=cell["location_id"],
                observation_ids=[],
                authenticity=cell["authenticity"],
                data_source=cell["provider"],
                quality_flag="validated",
                observation_timestamp=None,
                ingestion_timestamp=None,
                twin_metadata={},
            )

            try:
                assessments = evaluator.assess_observed(ti, cell["location_id"])
                for a in assessments:
                    if a.hazard_type == "unknown":
                        continue
                    entry = {
                        "location_id": cell["location_id"],
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "hazard": a.hazard_type,
                        "score": a.hazard_score,
                        "severity": a.severity.value,
                        "confidence": a.assessment_confidence,
                    }
                    if a.hazard_type == "heat":
                        heat_map.append(entry)
                    elif a.hazard_type == "heavy_rain":
                        rain_map.append(entry)
                    elif a.hazard_type == "dryness":
                        dry_map.append(entry)
            except Exception:
                pass

    def summarize(mp: list[dict], name: str) -> dict:
        if not mp:
            return {"hazard": name, "cells_affected": 0}
        scores = [e["score"] for e in mp]
        return {
            "hazard": name,
            "cells_affected": len(mp),
            "total_cells": cells_total,
            "max_score": round(max(scores), 1),
            "mean_score": round(sum(scores) / len(scores), 1),
            "top_cells": sorted(mp, key=lambda x: x["score"], reverse=True)[:3],
        }

    return {
        "summary": {
            "total_cells": cells_total,
            "heat": summarize(heat_map, "heat"),
            "heavy_rain": summarize(rain_map, "heavy_rain"),
            "dryness": summarize(dry_map, "dryness"),
        },
        "heat_map": heat_map,
        "rain_map": rain_map,
        "dry_map": dry_map,
    }
