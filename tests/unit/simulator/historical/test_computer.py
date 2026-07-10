from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from simulator.historical.computer import (
    BASELINE_SCHEMA,
    MIN_VALID_YEARS,
    SEASONS,
    VARIABLES,
    BaselineComputer,
    _compute_percentiles,
    _filter_by_variable,
    _get_obs_value,
    _get_season,
    _make_record,
)
from simulator.models.baseline import BaselineCollection, BaselineType
from simulator.models.weather import WeatherObservation

# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_get_obs_value():
    obs = WeatherObservation(
        location_id="loc1",
        latitude=10,
        longitude=20,
        timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        temperature_2m=25.0,
        precipitation_mm=0,
        humidity_pct=50,
        pressure_hpa=1013,
        wind_speed_10m=5,
        wind_direction_10m=180,
    )
    assert _get_obs_value(obs, "temperature_2m") == 25.0
    assert _get_obs_value(obs, "nonexistent") is None


def test_compute_percentiles_empty():
    result = _compute_percentiles(np.array([]))
    assert result == {"p05": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}


def test_compute_percentiles_single():
    arr = np.array([42.0])
    result = _compute_percentiles(arr)
    for v in result.values():
        assert v == 42.0


def test_compute_percentiles_values():
    arr = np.arange(1.0, 101.0)
    result = _compute_percentiles(arr)
    assert result["p05"] == pytest.approx(5.95, rel=0.1)
    assert result["p50"] == pytest.approx(50.5, rel=0.1)
    assert result["p95"] == pytest.approx(95.05, rel=0.1)
    assert "p25" in result
    assert "p75" in result


def test_filter_by_variable():
    obs_list = [
        WeatherObservation(
            location_id="loc1",
            latitude=10.0,
            longitude=20.0,
            timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            temperature_2m=25.0,
            precipitation_mm=0.0,
            humidity_pct=50.0,
            pressure_hpa=1013.0,
            wind_speed_10m=5.0,
            wind_direction_10m=180.0,
        ),
        WeatherObservation(
            location_id="loc1",
            latitude=10.0,
            longitude=20.0,
            timestamp=datetime(2020, 1, 2, tzinfo=UTC),
            temperature_2m=30.0,
            precipitation_mm=5.0,
            humidity_pct=60.0,
            pressure_hpa=1010.0,
            wind_speed_10m=3.0,
            wind_direction_10m=90.0,
        ),
    ]
    result = _filter_by_variable(obs_list, "temperature_2m")
    assert np.allclose(result, [25.0, 30.0])


def test_filter_by_variable_missing_attribute():
    class FakeObs:
        pass

    obs_list = [FakeObs()]
    result = _filter_by_variable(obs_list, "temperature_2m")
    assert len(result) == 0


def test_filter_by_variable_some_none():
    obs_list = [make_obs(temp=25.0), make_obs(temp=None), make_obs(temp=35.0)]
    result = _filter_by_variable(obs_list, "temperature_2m")
    assert np.allclose(result, [25.0, 35.0])


def test_get_season():
    assert _get_season(12) == "DJF"
    assert _get_season(1) == "DJF"
    assert _get_season(2) == "DJF"
    assert _get_season(3) == "MAM"
    assert _get_season(5) == "MAM"
    assert _get_season(6) == "JJA"
    assert _get_season(8) == "JJA"
    assert _get_season(9) == "SON"
    assert _get_season(11) == "SON"


def test_make_record():
    values = np.array([10.0, 20.0, 30.0])
    record = _make_record(
        location_id="loc1",
        variable="temperature_2m",
        btype=BaselineType.DAILY,
        period_start=date(2020, 1, 1),
        period_end=date(2020, 1, 1),
        values=values,
        valid_years=3,
        source="era5",
    )
    assert record.location_id == "loc1"
    assert record.variable == "temperature_2m"
    assert record.baseline_type == BaselineType.DAILY
    assert record.mean == 20.0
    assert record.std == 10.0
    assert record.min_value == 10.0
    assert record.max_value == 30.0
    assert record.sample_count == 3
    assert record.valid_years == 3
    assert record.source == "era5"


def test_make_record_empty():
    values = np.array([])
    record = _make_record(
        "loc1", "temp", BaselineType.DAILY, date(2020, 1, 1), date(2020, 1, 1), values, 0, "test"
    )
    assert record.mean == 0.0
    assert record.std == 0.0
    assert record.sample_count == 0


def test_make_record_single_value():
    values = np.array([42.0])
    record = _make_record(
        "loc1", "temp", BaselineType.DAILY, date(2020, 1, 1), date(2020, 1, 1), values, 1, "test"
    )
    assert record.mean == 42.0
    assert record.std == 0.0
    assert record.sample_count == 1


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_variables_defined():
    assert "temperature_2m" in VARIABLES
    assert "precipitation_mm" in VARIABLES
    assert len(VARIABLES) == 9


def test_seasons_defined():
    assert set(SEASONS.keys()) == {"DJF", "MAM", "JJA", "SON"}
    assert SEASONS["DJF"] == [12, 1, 2]


def test_baseline_schema():
    field_names = [f.name for f in BASELINE_SCHEMA]
    assert "baseline_id" in field_names
    assert "mean" in field_names
    assert "computed_at" in field_names


def test_min_valid_years():
    assert MIN_VALID_YEARS == 25


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def make_obs(
    location_id="loc1",
    temp=25.0,
    precip=0.0,
    humid=50.0,
    press=1013.0,
    wind=5.0,
    wdir=180.0,
    doy=1,
    year=2000,
):
    dt = datetime(year, 1, 1, tzinfo=UTC) + timedelta(days=doy - 1)
    return WeatherObservation(
        location_id=location_id,
        latitude=10.0,
        longitude=20.0,
        timestamp=dt,
        temperature_2m=temp,
        precipitation_mm=precip,
        humidity_pct=humid,
        pressure_hpa=press,
        wind_speed_10m=wind,
        wind_direction_10m=wdir,
    )


# ---------------------------------------------------------------------------
# BaselineComputer – init / _query_obs
# ---------------------------------------------------------------------------


def test_computer_init_defaults():
    computer = BaselineComputer()
    assert computer._store is not None
    assert computer._lock is not None


def test_computer_init_with_path(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    assert computer._baseline_path == tmp_path
    assert tmp_path.exists()


def test_query_obs_empty(monkeypatch):
    computer = BaselineComputer()
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: [])
    result = computer._query_obs("loc1", 2000, 2005)
    assert result == []


def test_query_obs_with_data(monkeypatch):
    computer = BaselineComputer()
    obs = [make_obs(year=2000), make_obs(year=2001)]
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs)
    result = computer._query_obs("loc1", 2000, 2005)
    assert result == obs


# ---------------------------------------------------------------------------
# compute_daily_climatology
# ---------------------------------------------------------------------------


def test_compute_daily_climatology_empty(monkeypatch):
    computer = BaselineComputer()
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: [])
    result = computer.compute_daily_climatology("loc1", "temperature_2m")
    assert result == {}


def test_compute_daily_climatology_insufficient_data(monkeypatch):
    computer = BaselineComputer()
    obs_list = [make_obs(doy=i, year=2020) for i in range(1, 10)]
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    result = computer.compute_daily_climatology("loc1", "temperature_2m", 2020, 2020)
    assert result == {}


def test_compute_daily_climatology_normal(monkeypatch):
    computer = BaselineComputer()
    obs_list = []
    for year in range(1991, 2021):
        obs_list.append(make_obs(doy=1, year=year, temp=20.0 + (year - 1991) * 0.5))
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    result = computer.compute_daily_climatology("loc1", "temperature_2m", 1991, 2020)
    assert 1 in result
    record = result[1]
    assert record.location_id == "loc1"
    assert record.variable == "temperature_2m"
    assert record.baseline_type == BaselineType.DAILY
    assert record.sample_count == 30
    assert record.valid_years == 30


def test_compute_daily_climatology_date_overflow(monkeypatch):
    """DOY 366 from leap years + end_year=9999 triggers OverflowError."""
    computer = BaselineComputer()
    obs_list = []
    for year in range(1991, 2021):
        obs_list.append(make_obs(doy=1, year=year, temp=20.0))
    # At least 25 obs at DOY 366 to pass MIN_VALID_YEARS filter
    leap_years = [y for y in range(1900, 2101) if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)]
    for y in leap_years:
        obs_list.append(
            WeatherObservation(
                location_id="loc1",
                latitude=10.0,
                longitude=20.0,
                timestamp=datetime(y, 12, 31, tzinfo=UTC),
                temperature_2m=25.0,
                precipitation_mm=0.0,
                humidity_pct=50.0,
                pressure_hpa=1013.0,
                wind_speed_10m=5.0,
                wind_direction_10m=180.0,
            )
        )
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    # end_year=9999 makes date(9999,1,1)+timedelta(365) overflow
    result = computer.compute_daily_climatology("loc1", "temperature_2m", 1900, 9999)
    assert 1 in result
    assert 366 not in result  # skipped due to OverflowError


# ---------------------------------------------------------------------------
# compute_monthly_climatology
# ---------------------------------------------------------------------------


def test_compute_monthly_climatology_empty(monkeypatch):
    computer = BaselineComputer()
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: [])
    result = computer.compute_monthly_climatology("loc1", "temperature_2m")
    assert result == {}


def test_compute_monthly_climatology(monkeypatch):
    computer = BaselineComputer()
    obs_list = []
    for year in range(1991, 2021):
        for month in [1, 6]:
            dt = datetime(year, month, 1, tzinfo=UTC)
            obs_list.append(
                WeatherObservation(
                    location_id="loc1",
                    latitude=10.0,
                    longitude=20.0,
                    timestamp=dt,
                    temperature_2m=25.0,
                    precipitation_mm=0.0,
                    humidity_pct=50.0,
                    pressure_hpa=1013.0,
                    wind_speed_10m=5.0,
                    wind_direction_10m=180.0,
                )
            )
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    result = computer.compute_monthly_climatology("loc1", "temperature_2m", 1991, 2020)
    assert 1 in result
    assert 6 in result
    assert result[1].sample_count == 30


def test_compute_monthly_climatology_insufficient(monkeypatch):
    """Fewer than MIN_VALID_YEARS observations per month."""
    computer = BaselineComputer()
    obs_list = [make_obs(year=2020, doy=15)]  # January
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    result = computer.compute_monthly_climatology("loc1", "temperature_2m", 2020, 2020)
    assert result == {}


# ---------------------------------------------------------------------------
# compute_seasonal_climatology
# ---------------------------------------------------------------------------


def test_compute_seasonal_climatology_empty(monkeypatch):
    computer = BaselineComputer()
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: [])
    result = computer.compute_seasonal_climatology("loc1", "temperature_2m")
    assert result == {}


def test_compute_seasonal_climatology(monkeypatch):
    computer = BaselineComputer()
    obs_list = []
    for year in range(1991, 2021):
        for month in [1, 4, 7, 10]:
            dt = datetime(year, month, 1, tzinfo=UTC)
            obs_list.append(
                WeatherObservation(
                    location_id="loc1",
                    latitude=10.0,
                    longitude=20.0,
                    timestamp=dt,
                    temperature_2m=25.0,
                    precipitation_mm=0.0,
                    humidity_pct=50.0,
                    pressure_hpa=1013.0,
                    wind_speed_10m=5.0,
                    wind_direction_10m=180.0,
                )
            )
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    result = computer.compute_seasonal_climatology("loc1", "temperature_2m", 1991, 2020)
    assert "DJF" in result or "MAM" in result or "JJA" in result or "SON" in result


# ---------------------------------------------------------------------------
# compute_rolling_climatology
# ---------------------------------------------------------------------------


def test_compute_rolling_climatology_empty(monkeypatch):
    computer = BaselineComputer()
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: [])
    result = computer.compute_rolling_climatology("loc1", "temperature_2m")
    assert result == {}


def test_compute_rolling_climatology_basic(monkeypatch):
    computer = BaselineComputer()
    today = date(2023, 6, 15)
    obs_list = []
    # One observation per day for 60 consecutive days, 25+ years of data
    for year in range(1993, 2024):
        for day_offset in range(60):
            dt = datetime(year, 6, 1, tzinfo=UTC) + timedelta(days=day_offset)
            obs_list.append(
                WeatherObservation(
                    location_id="loc1",
                    latitude=10.0,
                    longitude=20.0,
                    timestamp=dt,
                    temperature_2m=20.0 + (year - 1993) * 0.2,
                    precipitation_mm=0.0,
                    humidity_pct=50.0,
                    pressure_hpa=1013.0,
                    wind_speed_10m=5.0,
                    wind_direction_10m=180.0,
                )
            )
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    with patch("simulator.historical.computer.date", wraps=date) as mock_date:
        mock_date.today.return_value = today
        result = computer.compute_rolling_climatology("loc1", "temperature_2m", window_days=30)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# compute_full_climatology
# ---------------------------------------------------------------------------


def test_compute_full_climatology(monkeypatch):
    computer = BaselineComputer()
    obs_list = []
    for year in range(1991, 2021):
        obs_list.append(make_obs(doy=1, year=year, temp=25.0))
        obs_list.append(make_obs(doy=2, year=year, temp=26.0))
    monkeypatch.setattr(computer._store, "query_observations", lambda *_, **__: obs_list)
    result = computer.compute_full_climatology("loc1", 1991, 2020)
    assert result.location_id == "loc1"


# ---------------------------------------------------------------------------
# save_climatology
# ---------------------------------------------------------------------------


def test_save_climatology_empty():
    computer = BaselineComputer()
    collection = BaselineCollection(location_id="loc1")
    computer.save_climatology(collection)


def test_save_climatology_non_empty(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    collection = BaselineCollection(location_id="loc1")
    values = np.array([10.0, 20.0, 30.0])
    record = _make_record(
        "loc1",
        "temperature_2m",
        BaselineType.DAILY,
        date(2020, 1, 1),
        date(2020, 1, 1),
        values,
        3,
        "era5",
    )
    collection.daily["temperature_2m"] = record
    computer.save_climatology(collection)
    parquet_files = sorted((tmp_path / "loc1").glob("climatology_*.parquet"))
    assert len(parquet_files) == 1


# ---------------------------------------------------------------------------
# load_climatology
# ---------------------------------------------------------------------------


def test_load_climatology_no_dir(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    result = computer.load_climatology("nonexistent")
    assert result is None


def test_load_climatology_no_files(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    (tmp_path / "loc1").mkdir(parents=True)
    result = computer.load_climatology("loc1")
    assert result is None


def test_load_climatology_happy_path(tmp_path):
    """Save then load — verify round-trip."""
    computer = BaselineComputer(baseline_path=tmp_path)
    collection = BaselineCollection(location_id="loc1")

    values = np.array([10.0, 20.0, 30.0])
    daily_rec = _make_record(
        "loc1",
        "temperature_2m",
        BaselineType.DAILY,
        date(2020, 1, 1),
        date(2020, 1, 1),
        values,
        3,
        "era5",
    )
    collection.daily["temperature_2m"] = daily_rec

    monthly_rec = _make_record(
        "loc1",
        "precipitation_mm",
        BaselineType.MONTHLY,
        date(2020, 1, 1),
        date(2020, 1, 1),
        values,
        3,
        "era5",
    )
    collection.monthly["precipitation_mm_month_1"] = monthly_rec

    seasonal_rec = _make_record(
        "loc1",
        "humidity_pct",
        BaselineType.SEASONAL,
        date(2020, 1, 1),
        date(2020, 3, 1),
        values,
        3,
        "era5",
    )
    collection.seasonal["humidity_pct_DJF"] = seasonal_rec

    computer.save_climatology(collection)
    loaded = computer.load_climatology("loc1")
    assert loaded is not None
    assert loaded.location_id == "loc1"
    assert "temperature_2m" in loaded.daily
    assert "precipitation_mm_month_1" in loaded.monthly
    assert "humidity_pct_DJF" in loaded.seasonal


# ---------------------------------------------------------------------------
# get_baseline_for_date
# ---------------------------------------------------------------------------


def test_get_baseline_for_date_no_collection(monkeypatch):
    computer = BaselineComputer()
    monkeypatch.setattr(computer, "load_climatology", lambda *_, **__: None)
    result = computer.get_baseline_for_date("loc1", "temperature_2m", date(2020, 6, 15))
    assert result is None


def test_get_baseline_for_date_from_daily(monkeypatch):
    computer = BaselineComputer()
    collection = BaselineCollection(location_id="loc1")
    monkeypatch.setattr(computer, "load_climatology", lambda *_, **__: collection)

    daily_rec = _make_record(
        "loc1",
        "temperature_2m",
        BaselineType.DAILY,
        date(2020, 1, 1),
        date(2020, 1, 1),
        np.array([15.0]),
        1,
        "era5",
    )
    monkeypatch.setattr(computer, "_load_daily_records", lambda *_, **__: {1: daily_rec})
    result = computer.get_baseline_for_date("loc1", "temperature_2m", date(2020, 1, 1))
    assert result is not None
    assert result == daily_rec


def test_get_baseline_for_date_from_monthly(monkeypatch):
    computer = BaselineComputer()
    collection = BaselineCollection(location_id="loc1")
    monthly_rec = _make_record(
        "loc1",
        "temperature_2m",
        BaselineType.MONTHLY,
        date(2020, 6, 1),
        date(2020, 6, 1),
        np.array([20.0]),
        1,
        "era5",
    )
    collection.monthly["temperature_2m_month_6"] = monthly_rec
    monkeypatch.setattr(computer, "load_climatology", lambda *_, **__: collection)
    monkeypatch.setattr(computer, "_load_daily_records", lambda *_, **__: None)
    result = computer.get_baseline_for_date("loc1", "temperature_2m", date(2020, 6, 15))
    assert result == monthly_rec


def test_get_baseline_for_date_from_seasonal(monkeypatch):
    computer = BaselineComputer()
    collection = BaselineCollection(location_id="loc1")
    seasonal_rec = _make_record(
        "loc1",
        "temperature_2m",
        BaselineType.SEASONAL,
        date(2020, 12, 1),
        date(2020, 2, 1),
        np.array([10.0]),
        1,
        "era5",
    )
    collection.seasonal["temperature_2m_DJF"] = seasonal_rec
    monkeypatch.setattr(computer, "load_climatology", lambda *_, **__: collection)
    monkeypatch.setattr(computer, "_load_daily_records", lambda *_, **__: {})
    result = computer.get_baseline_for_date("loc1", "temperature_2m", date(2020, 12, 25))
    assert result == seasonal_rec


def test_get_baseline_for_date_falls_through(monkeypatch):
    """When no daily, monthly, or seasonal record exists, return None."""
    computer = BaselineComputer()
    collection = BaselineCollection(location_id="loc1")
    monkeypatch.setattr(computer, "load_climatology", lambda *_, **__: collection)
    monkeypatch.setattr(computer, "_load_daily_records", lambda *_, **__: {})
    result = computer.get_baseline_for_date("loc1", "temperature_2m", date(2020, 6, 15))
    assert result is None


# ---------------------------------------------------------------------------
# _load_daily_records
# ---------------------------------------------------------------------------


def test_load_daily_records_no_dir(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    result = computer._load_daily_records("nonexistent", "temperature_2m")
    assert result is None


def test_load_daily_records_no_files(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    (tmp_path / "loc1").mkdir(parents=True)
    result = computer._load_daily_records("loc1", "temperature_2m")
    assert result is None


def test_load_daily_records_happy(tmp_path):
    computer = BaselineComputer(baseline_path=tmp_path)
    (tmp_path / "loc1").mkdir(parents=True)

    arrays = {
        "baseline_id": ["id1", "id2"],
        "location_id": ["loc1", "loc1"],
        "variable": ["temperature_2m", "temperature_2m"],
        "baseline_type": ["daily", "daily"],
        "period_start": [date(2020, 1, 1), date(2020, 1, 2)],
        "period_end": [date(2020, 1, 1), date(2020, 1, 2)],
        "mean": [15.0, 20.0],
        "std": [1.0, 2.0],
        "min_value": [10.0, 15.0],
        "max_value": [20.0, 25.0],
        "p05": [11.0, 16.0],
        "p25": [12.0, 17.0],
        "p50": [15.0, 20.0],
        "p75": [18.0, 23.0],
        "p95": [19.0, 24.0],
        "sample_count": [30, 30],
        "valid_years": [30, 30],
        "source": ["era5", "era5"],
        "version": ["1.0.0", "1.0.0"],
        "computed_at": [datetime(2023, 1, 1, tzinfo=UTC), datetime(2023, 1, 1, tzinfo=UTC)],
    }
    batch = pa.RecordBatch.from_pydict(arrays, schema=BASELINE_SCHEMA)
    table = pa.Table.from_batches([batch])
    pq.write_table(
        table, tmp_path / "loc1" / "climatology_20230101_120000.parquet", compression="zstd"
    )

    result = computer._load_daily_records("loc1", "temperature_2m")
    assert result is not None
    assert 1 in result
    assert 2 in result
    assert result[1].mean == 15.0
    assert result[2].mean == 20.0


def test_load_daily_records_filters_variable(tmp_path):
    """Only records matching the requested variable are returned."""
    computer = BaselineComputer(baseline_path=tmp_path)
    (tmp_path / "loc1").mkdir(parents=True)

    arrays = {
        "baseline_id": ["id1", "id2"],
        "location_id": ["loc1", "loc1"],
        "variable": ["temperature_2m", "precipitation_mm"],
        "baseline_type": ["daily", "daily"],
        "period_start": [date(2020, 1, 1), date(2020, 1, 1)],
        "period_end": [date(2020, 1, 1), date(2020, 1, 1)],
        "mean": [15.0, 5.0],
        "std": [1.0, 1.0],
        "min_value": [10.0, 2.0],
        "max_value": [20.0, 8.0],
        "p05": [11.0, 3.0],
        "p25": [12.0, 4.0],
        "p50": [15.0, 5.0],
        "p75": [18.0, 6.0],
        "p95": [19.0, 7.0],
        "sample_count": [30, 30],
        "valid_years": [30, 30],
        "source": ["era5", "era5"],
        "version": ["1.0.0", "1.0.0"],
        "computed_at": [datetime(2023, 1, 1, tzinfo=UTC), datetime(2023, 1, 1, tzinfo=UTC)],
    }
    batch = pa.RecordBatch.from_pydict(arrays, schema=BASELINE_SCHEMA)
    table = pa.Table.from_batches([batch])
    pq.write_table(
        table, tmp_path / "loc1" / "climatology_20230101_120000.parquet", compression="zstd"
    )

    result = computer._load_daily_records("loc1", "temperature_2m")
    assert result is not None
    assert len(result) == 1
    assert result[1].mean == 15.0
