"""Full 651-cell Karnataka ERA5 spatial dashboard."""

from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import folium
import numpy as np
import pandas as pd
import streamlit as st
import xarray as xr
from streamlit_folium import st_folium

from dashboard.config.config import DEFAULT_ZOOM, SAMPLE_LOCATIONS

logger = logging.getLogger(__name__)
DATA_DIR = Path("data/validation/era5/karnataka/raw")


@st.cache_resource
def _load_month(year: int, month: int) -> tuple[xr.Dataset, xr.Dataset | None]:
    """Open one CDS ZIP-wrapped Karnataka month."""
    fp = DATA_DIR / f"era5_{year}{month:02d}.nc"
    if not fp.exists():
        raise FileNotFoundError(fp)
    z = zipfile.ZipFile(fp)
    names = z.namelist()

    def open_member(name: str) -> xr.Dataset:
        tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False)
        try:
            tmp.write(z.read(name))
            tmp.close()
            ds = xr.open_dataset(tmp.name).load()
            ds.close()
            return ds
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    instant = next(n for n in names if n.endswith(".nc") and "instant" in n)
    accum = next((n for n in names if n.endswith(".nc") and "accum" in n), None)
    return open_member(instant), open_member(accum) if accum else None


def _frame(ds: xr.Dataset, acc: xr.Dataset | None, time_idx: int) -> pd.DataFrame:
    lats = ds.latitude.values
    lons = ds.longitude.values
    t = ds.t2m.isel(valid_time=time_idx).values - 273.15
    d = ds.d2m.isel(valid_time=time_idx).values - 273.15
    p = ds.sp.isel(valid_time=time_idx).values / 100.0
    wind = np.sqrt(
        ds.u10.isel(valid_time=time_idx).values ** 2 + ds.v10.isel(valid_time=time_idx).values ** 2
    )
    rh = np.clip(
        100.0
        * np.exp(17.625 * (d + 273.15) / (d + 273.15 + 243.04))
        / np.exp(17.625 * (t + 273.15) / (t + 273.15 + 243.04)),
        0,
        100,
    )
    rainfall = (
        acc.tp.isel(valid_time=time_idx).values * 1000.0
        if acc is not None and "tp" in acc
        else np.zeros_like(t)
    )
    # ET0 is deliberately labeled an estimate: this view has hourly T2M,
    # not daily Tmax/Tmin, so the FAO temperature-only approximation is used.
    et0 = np.maximum(0.0, 0.0023 * (t + 17.8) * np.sqrt(5.0) * 25.0)
    timestamp = ds.valid_time.isel(valid_time=time_idx).values
    return pd.DataFrame(
        {
            "latitude": np.repeat(lats, len(lons)),
            "longitude": np.tile(lons, len(lats)),
            "timestamp": timestamp,
            "temperature_c": t.ravel(),
            "rainfall_mm": rainfall.ravel(),
            "humidity_pct": rh.ravel(),
            "pressure_hpa": p.ravel(),
            "wind_speed_ms": wind.ravel(),
            "et0_mm": et0.ravel(),
        }
    )


def _value_color(value: float, low: float, high: float) -> str:
    ratio = max(0.0, min(1.0, (value - low) / (high - low + 1e-9)))
    return f"#{int(255 * ratio):02x}33{int(255 * (1 - ratio)):02x}"


def _backend_overlay(api: Any, row: pd.Series) -> dict[str, Any]:
    """Fetch backend forecast/risk for the selected real grid cell."""
    location_id = f"grid-{row.latitude:.2f}-{row.longitude:.2f}"
    result: dict[str, Any] = {"location_id": location_id}
    try:
        forecast = api.get_forecast(location_id, horizon=3) or []
        result["forecast"] = forecast[0] if forecast else None
    except Exception as exc:
        logger.warning("Forecast overlay unavailable: %s", exc)
        result["forecast"] = None
    try:
        result["hazard"] = api.get_risk(location_id) if api else None
    except Exception as exc:
        logger.warning("Risk overlay unavailable: %s", exc)
        result["hazard"] = None
    return result


def render(api: Any, filters: dict[str, Any]) -> None:
    st.title("Karnataka Spatial Grid")
    st.markdown(
        "Full 651-cell ERA5 grid at native 0.25° resolution. All base layers are REAL ERA5 data."
    )

    years = [year for year in (2021, 2022, 2023) if (DATA_DIR / f"era5_{year}01.nc").exists()]
    if not years:
        st.error("No Karnataka ERA5 dataset found.")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("Year", years, index=len(years) - 1)
    with col2:
        months = [m for m in range(1, 13) if (DATA_DIR / f"era5_{year}{m:02d}.nc").exists()]
        month = st.selectbox("Month", months, format_func=lambda m: f"{year}-{m:02d}")
    ds, acc = _load_month(year, month)
    with col3:
        time_idx = st.slider(
            "Time step", 0, int(ds.sizes["valid_time"]) - 1, int(ds.sizes["valid_time"]) - 1
        )
    if st.button("Advance animation"):
        st.session_state["spatial_time"] = (time_idx + 1) % int(ds.sizes["valid_time"])
        st.rerun()
    time_idx = st.session_state.get("spatial_time", time_idx)

    df = _frame(ds, acc, time_idx)
    variables = {
        "Temperature": "temperature_c",
        "Rainfall": "rainfall_mm",
        "Humidity": "humidity_pct",
        "Pressure": "pressure_hpa",
        "Wind": "wind_speed_ms",
        "ET0 estimate": "et0_mm",
    }
    layer = st.selectbox("Layer", [*variables, "Forecast", "Hazard", "Scenario", "Interpolation"])
    field = variables.get(layer, "temperature_c")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Grid cells", f"{len(df):,}")
    c2.metric("Timestamp", str(df.timestamp.iloc[0])[:16])
    c3.metric("Mean", f"{df[field].mean():.2f}")
    c4.metric("Range", f"{df[field].min():.2f}–{df[field].max():.2f}")

    center = [float(df.latitude.mean()), float(df.longitude.mean())]
    m = folium.Map(
        location=center, zoom_start=DEFAULT_ZOOM, tiles="CartoDB positron", control_scale=True
    )
    grid_group = folium.FeatureGroup(name=f"651-cell {layer}", show=True)
    values = df[field]
    low, high = float(values.quantile(0.05)), float(values.quantile(0.95))
    for row in df.itertuples():
        tooltip = (
            f"Grid cell ({row.latitude:.2f}, {row.longitude:.2f})<br>"
            f"Temperature: {row.temperature_c:.1f} °C<br>"
            f"Rainfall: {row.rainfall_mm:.2f} mm<br>"
            f"Humidity: {row.humidity_pct:.1f}%<br>"
            f"Pressure: {row.pressure_hpa:.1f} hPa<br>"
            f"Wind: {row.wind_speed_ms:.1f} m/s<br>"
            f"ET0 estimate: {row.et0_mm:.2f} mm"
        )
        folium.CircleMarker(
            [row.latitude, row.longitude],
            radius=7 if layer == "Interpolation" else 5,
            color=_value_color(float(getattr(row, field)), low, high),
            fill=True,
            fill_opacity=0.75,
            tooltip=tooltip,
        ).add_to(grid_group)
    grid_group.add_to(m)

    district_group = folium.FeatureGroup(name="District overlay", show=True)
    for location in SAMPLE_LOCATIONS:
        folium.Marker(
            [location["lat"], location["lon"]],
            tooltip=location["district"],
            icon=folium.Icon(color="black", icon="info-sign"),
        ).add_to(district_group)
    district_group.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    map_state = st_folium(m, width="100%", height=600, returned_objects=["last_object_clicked"])

    st.subheader("Selected cell")
    selected_lat = st.number_input(
        "Latitude",
        value=12.97,
        min_value=float(df.latitude.min()),
        max_value=float(df.latitude.max()),
        step=0.25,
    )
    selected_lon = st.number_input(
        "Longitude",
        value=77.59,
        min_value=float(df.longitude.min()),
        max_value=float(df.longitude.max()),
        step=0.25,
    )
    selected = df.iloc[
        ((df.latitude - selected_lat).abs() + (df.longitude - selected_lon).abs()).argmin()
    ]
    st.dataframe(selected.to_frame("value"), use_container_width=True)

    if layer in {"Forecast", "Hazard", "Scenario"}:
        overlay = _backend_overlay(api, selected)
        st.json(overlay)
        st.caption(
            "Forecast and hazard values are shown only when returned by the live backend; no synthetic spatial values are created."
        )

    st.subheader("Regional statistics")
    st.dataframe(
        df[
            [
                "temperature_c",
                "rainfall_mm",
                "humidity_pct",
                "pressure_hpa",
                "wind_speed_ms",
                "et0_mm",
            ]
        ]
        .describe()
        .round(2),
        use_container_width=True,
    )
    if map_state and map_state.get("last_object_clicked"):
        st.caption(
            "Map selection received. Use the coordinate controls above to inspect the nearest cell."
        )
