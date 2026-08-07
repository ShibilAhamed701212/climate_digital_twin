from __future__ import annotations

import logging
import threading
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from simulator.configs.twin_config import resolve_subdir
from simulator.models.baseline import BaselineCollection, BaselineRecord, BaselineType
from simulator.models.weather import WeatherObservation
from simulator.repository.parquet_store import ParquetObservationStore

_logger = logging.getLogger(__name__)

BASELINE_SCHEMA = pa.schema(
    [
        pa.field("baseline_id", pa.string()),
        pa.field("location_id", pa.string()),
        pa.field("variable", pa.string()),
        pa.field("baseline_type", pa.string()),
        pa.field("period_start", pa.date32()),
        pa.field("period_end", pa.date32()),
        pa.field("mean", pa.float64()),
        pa.field("std", pa.float64()),
        pa.field("min_value", pa.float64()),
        pa.field("max_value", pa.float64()),
        pa.field("p05", pa.float64()),
        pa.field("p25", pa.float64()),
        pa.field("p50", pa.float64()),
        pa.field("p75", pa.float64()),
        pa.field("p95", pa.float64()),
        pa.field("sample_count", pa.int64()),
        pa.field("valid_years", pa.int64()),
        pa.field("source", pa.string()),
        pa.field("version", pa.string()),
        pa.field("computed_at", pa.timestamp("us", tz="UTC")),
    ]
)

VARIABLES = [
    "temperature_2m",
    "precipitation_mm",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_10m",
    "wind_direction_10m",
    "solar_radiation",
    "cloud_cover_pct",
    "soil_moisture",
]

SEASONS = {"DJF": [12, 1, 2], "MAM": [3, 4, 5], "JJA": [6, 7, 8], "SON": [9, 10, 11]}
MIN_VALID_YEARS = 25


def _get_obs_value(obs: WeatherObservation, variable: str) -> float | None:
    return getattr(obs, variable, None)


def _filter_by_variable(obs_list: list[WeatherObservation], variable: str) -> np.ndarray:
    values = [_get_obs_value(o, variable) for o in obs_list]
    clean = [v for v in values if v is not None]
    return np.array(clean, dtype=np.float64)


def _compute_percentiles(values: np.ndarray) -> dict[str, float]:
    if len(values) == 0:
        return {"p05": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}
    return {
        "p05": float(np.percentile(values, 5)),
        "p25": float(np.percentile(values, 25)),
        "p50": float(np.percentile(values, 50)),
        "p75": float(np.percentile(values, 75)),
        "p95": float(np.percentile(values, 95)),
    }


def _get_season(month: int) -> str:
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8):
        return "JJA"
    return "SON"


def _make_record(
    location_id: str,
    variable: str,
    btype: BaselineType,
    period_start: date,
    period_end: date,
    values: np.ndarray,
    valid_years: int,
    source: str,
) -> BaselineRecord:
    percentiles = _compute_percentiles(values)
    return BaselineRecord(
        location_id=location_id,
        variable=variable,
        baseline_type=btype,
        period_start=period_start,
        period_end=period_end,
        mean=float(np.mean(values)) if len(values) > 0 else 0.0,
        std=float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        min_value=float(np.min(values)) if len(values) > 0 else 0.0,
        max_value=float(np.max(values)) if len(values) > 0 else 0.0,
        p05=percentiles["p05"],
        p25=percentiles["p25"],
        p50=percentiles["p50"],
        p75=percentiles["p75"],
        p95=percentiles["p95"],
        sample_count=len(values),
        valid_years=valid_years,
        source=source,
    )


class BaselineComputer:
    def __init__(
        self, store: ParquetObservationStore | None = None, baseline_path: Path | None = None
    ) -> None:
        self._store = store or ParquetObservationStore()
        self._baseline_path = baseline_path or resolve_subdir("baselines")
        self._baseline_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _query_obs(
        self, location_id: str, start_year: int, end_year: int
    ) -> list[WeatherObservation]:
        start_dt = datetime(start_year, 1, 1, tzinfo=UTC)
        end_dt = datetime(end_year, 12, 31, 23, 59, 59, tzinfo=UTC)
        return self._store.query_observations(
            location_id=location_id, start_time=start_dt, end_time=end_dt
        )

    def compute_daily_climatology(
        self,
        location_id: str,
        variable: str,
        start_year: int = 1991,
        end_year: int = 2020,
        source: str = "era5",
    ) -> dict[int, BaselineRecord]:
        records: dict[int, BaselineRecord] = {}
        obs_list = self._query_obs(location_id, start_year, end_year)
        if not obs_list:
            return records
        obs_by_doy: dict[int, list[WeatherObservation]] = {}
        for o in obs_list:
            doy = o.timestamp.timetuple().tm_yday
            if doy not in obs_by_doy:
                obs_by_doy[doy] = []
            obs_by_doy[doy].append(o)
        unique_years = set(o.timestamp.year for o in obs_list)
        for doy in range(1, 367):
            doy_obs = obs_by_doy.get(doy, [])
            values = _filter_by_variable(doy_obs, variable)
            if len(values) < MIN_VALID_YEARS:
                continue
            try:
                period_start = date(end_year, 1, 1) + timedelta(days=doy - 1)
            except (ValueError, OverflowError):
                continue
            records[doy] = _make_record(
                location_id,
                variable,
                BaselineType.DAILY,
                period_start,
                period_start,
                values,
                len(unique_years),
                source,
            )
        return records

    def compute_monthly_climatology(
        self,
        location_id: str,
        variable: str,
        start_year: int = 1991,
        end_year: int = 2020,
        source: str = "era5",
    ) -> dict[int, BaselineRecord]:
        records: dict[int, BaselineRecord] = {}
        obs_list = self._query_obs(location_id, start_year, end_year)
        if not obs_list:
            return records
        obs_by_month: dict[int, list[WeatherObservation]] = {}
        for o in obs_list:
            m = o.timestamp.month
            if m not in obs_by_month:
                obs_by_month[m] = []
            obs_by_month[m].append(o)
        unique_years = set(o.timestamp.year for o in obs_list)
        for month in range(1, 13):
            month_obs = obs_by_month.get(month, [])
            values = _filter_by_variable(month_obs, variable)
            if len(values) < MIN_VALID_YEARS:
                continue
            records[month] = _make_record(
                location_id,
                variable,
                BaselineType.MONTHLY,
                date(end_year, month, 1),
                date(end_year, month, 1),
                values,
                len(unique_years),
                source,
            )
        return records

    def compute_seasonal_climatology(
        self,
        location_id: str,
        variable: str,
        start_year: int = 1991,
        end_year: int = 2020,
        source: str = "era5",
    ) -> dict[str, BaselineRecord]:
        records: dict[str, BaselineRecord] = {}
        obs_list = self._query_obs(location_id, start_year, end_year)
        if not obs_list:
            return records
        obs_by_season: dict[str, list[WeatherObservation]] = {}
        for o in obs_list:
            m = o.timestamp.month
            for season, months in SEASONS.items():
                if m in months:
                    if season not in obs_by_season:
                        obs_by_season[season] = []
                    obs_by_season[season].append(o)
                    break
        unique_years = set(o.timestamp.year for o in obs_list)
        month_map = {"DJF": (12, 2), "MAM": (3, 5), "JJA": (6, 8), "SON": (9, 11)}
        for season_name, season_obs in obs_by_season.items():
            values = _filter_by_variable(season_obs, variable)
            if len(values) < MIN_VALID_YEARS:
                continue
            start_m, end_m = month_map.get(season_name, (1, 12))
            records[season_name] = _make_record(
                location_id,
                variable,
                BaselineType.SEASONAL,
                date(end_year, start_m, 1),
                date(end_year, min(end_m, 12), 1),
                values,
                len(unique_years),
                source,
            )
        return records

    def compute_rolling_climatology(
        self, location_id: str, variable: str, window_days: int = 30, source: str = "era5"
    ) -> dict[date, BaselineRecord]:
        records: dict[date, BaselineRecord] = {}
        today = date.today()
        start = today - timedelta(days=365 * 30)
        obs_list = self._query_obs(location_id, start.year, today.year)
        if not obs_list:
            return records
        obs_by_date: dict[date, list[float]] = {}
        for o in obs_list:
            val = _get_obs_value(o, variable)
            if val is not None:
                d = o.timestamp.date()
                if d not in obs_by_date:
                    obs_by_date[d] = []
                obs_by_date[d].append(val)
        sorted_dates = sorted(obs_by_date.keys())
        window_values: list[float] = []
        years_in_window: set[int] = set()
        for i, d in enumerate(sorted_dates):
            window_values.extend(obs_by_date[d])
            years_in_window.add(d.year)
            cutoff = d - timedelta(days=window_days)
            while i > 0 and sorted_dates[0] <= cutoff:
                first_date = sorted_dates.pop(0)
                removed_count = len(obs_by_date[first_date])
                window_values = window_values[removed_count:]
                years_in_window = set(dd.year for dd in sorted_dates[: i + 1] if dd in obs_by_date)
            if len(window_values) >= MIN_VALID_YEARS:
                arr = np.array(window_values, dtype=np.float64)
                records[d] = _make_record(
                    location_id,
                    variable,
                    BaselineType.ROLLING,
                    d - timedelta(days=window_days),
                    d,
                    arr,
                    len(years_in_window),
                    source,
                )
        return records

    def compute_full_climatology(
        self, location_id: str, start_year: int = 1991, end_year: int = 2020, source: str = "era5"
    ) -> BaselineCollection:
        collection = BaselineCollection(location_id=location_id)
        for variable in VARIABLES:
            daily = self.compute_daily_climatology(
                location_id, variable, start_year, end_year, source
            )
            if daily:
                collection.daily[variable] = list(daily.values())[0]
            monthly = self.compute_monthly_climatology(
                location_id, variable, start_year, end_year, source
            )
            if monthly:
                for month, record in monthly.items():
                    collection.monthly[f"{variable}_month_{month}"] = record
            seasonal = self.compute_seasonal_climatology(
                location_id, variable, start_year, end_year, source
            )
            if seasonal:
                for season, record in seasonal.items():
                    collection.seasonal[f"{variable}_{season}"] = record
        return collection

    def save_climatology(self, collection: BaselineCollection) -> None:
        records: list[BaselineRecord] = []
        records.extend(collection.daily.values())
        records.extend(collection.monthly.values())
        records.extend(collection.seasonal.values())
        if not records:
            return
        now = datetime.now(UTC)
        arrays = {
            "baseline_id": [r.baseline_id for r in records],
            "location_id": [r.location_id for r in records],
            "variable": [r.variable for r in records],
            "baseline_type": [r.baseline_type.value for r in records],
            "period_start": [r.period_start for r in records],
            "period_end": [r.period_end for r in records],
            "mean": [r.mean for r in records],
            "std": [r.std for r in records],
            "min_value": [r.min_value for r in records],
            "max_value": [r.max_value for r in records],
            "p05": [r.p05 for r in records],
            "p25": [r.p25 for r in records],
            "p50": [r.p50 for r in records],
            "p75": [r.p75 for r in records],
            "p95": [r.p95 for r in records],
            "sample_count": [r.sample_count for r in records],
            "valid_years": [r.valid_years for r in records],
            "source": [r.source for r in records],
            "version": [r.version for r in records],
            "computed_at": [now for _ in records],
        }
        batch = pa.RecordBatch.from_pydict(arrays, schema=BASELINE_SCHEMA)
        table = pa.Table.from_batches([batch])
        file_path = (
            self._baseline_path
            / collection.location_id
            / f"climatology_{now.strftime('%Y%m%d_%H%M%S')}.parquet"
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            pq.write_table(table, file_path, compression="zstd")

    def load_climatology(self, location_id: str) -> BaselineCollection | None:
        location_dir = self._baseline_path / location_id
        if not location_dir.exists():
            return None
        parquet_files = sorted(location_dir.glob("climatology_*.parquet"))
        if not parquet_files:
            return None
        latest = parquet_files[-1]
        table = pq.read_table(latest)
        collection = BaselineCollection(location_id=location_id)
        for row_idx in range(table.num_rows):
            row = {fn: table.column(fn)[row_idx].as_py() for fn in BASELINE_SCHEMA.names}
            record = BaselineRecord(
                baseline_id=row["baseline_id"],
                location_id=row["location_id"],
                variable=row["variable"],
                baseline_type=BaselineType(row["baseline_type"]),
                period_start=row["period_start"],
                period_end=row["period_end"],
                mean=row["mean"],
                std=row["std"],
                min_value=row["min_value"],
                max_value=row["max_value"],
                p05=row["p05"],
                p25=row["p25"],
                p50=row["p50"],
                p75=row["p75"],
                p95=row["p95"],
                sample_count=row["sample_count"],
                valid_years=row["valid_years"],
                source=row["source"],
                version=row["version"],
                computed_at=row["computed_at"],
            )
            btype = record.baseline_type
            if btype == BaselineType.DAILY:
                collection.daily[record.variable] = record
            elif btype == BaselineType.MONTHLY:
                key = f"{record.variable}_month_{row['period_start'].month}"
                collection.monthly[key] = record
            elif btype == BaselineType.SEASONAL:
                season = _get_season(row["period_start"].month)
                collection.seasonal[f"{record.variable}_{season}"] = record
        return collection

    def get_baseline_for_date(
        self, location_id: str, variable: str, target_date: date
    ) -> BaselineRecord | None:
        collection = self.load_climatology(location_id)
        if collection is None:
            return None
        doy = target_date.timetuple().tm_yday
        month = target_date.month
        season = _get_season(month)
        daily_records = self._load_daily_records(location_id, variable)
        if daily_records and doy in daily_records:
            return daily_records[doy]
        monthly_key = f"{variable}_month_{month}"
        if monthly_key in collection.monthly:
            return collection.monthly[monthly_key]
        seasonal_key = f"{variable}_{season}"
        if seasonal_key in collection.seasonal:
            return collection.seasonal[seasonal_key]
        return None

    def _load_daily_records(
        self, location_id: str, variable: str
    ) -> dict[int, BaselineRecord] | None:
        location_dir = self._baseline_path / location_id
        if not location_dir.exists():
            return None
        parquet_files = sorted(location_dir.glob("climatology_*.parquet"))
        if not parquet_files:
            return None
        latest = parquet_files[-1]
        table = pq.read_table(latest)
        daily_mask = pc.equal(table.column("baseline_type"), pa.scalar("daily"))
        var_mask = pc.equal(table.column("variable"), pa.scalar(variable))
        combined = pc.and_(daily_mask, var_mask)
        filtered = table.filter(combined)
        records: dict[int, BaselineRecord] = {}
        for row_idx in range(filtered.num_rows):
            row = {fn: filtered.column(fn)[row_idx].as_py() for fn in BASELINE_SCHEMA.names}
            doy = row["period_start"].timetuple().tm_yday
            records[doy] = BaselineRecord(
                baseline_id=row["baseline_id"],
                location_id=row["location_id"],
                variable=row["variable"],
                baseline_type=BaselineType(row["baseline_type"]),
                period_start=row["period_start"],
                period_end=row["period_end"],
                mean=row["mean"],
                std=row["std"],
                min_value=row["min_value"],
                max_value=row["max_value"],
                p05=row["p05"],
                p25=row["p25"],
                p50=row["p50"],
                p75=row["p75"],
                p95=row["p95"],
                sample_count=row["sample_count"],
                valid_years=row["valid_years"],
                source=row["source"],
                version=row["version"],
                computed_at=row["computed_at"],
            )
        return records
