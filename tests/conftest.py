import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)


@pytest.fixture(autouse=True)
def set_random_seed():
    np.random.seed(42)


@pytest.fixture
def sample_climate_data():
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    return pd.DataFrame({
        "Date": dates,
        "Latitude": 12.97,
        "Longitude": 77.59,
        "Rainfall": np.random.exponential(5, 100),
        "MaxTemp": np.random.uniform(25, 38, 100),
        "MinTemp": np.random.uniform(15, 22, 100),
    })


@pytest.fixture
def sample_processed_data():
    return pd.DataFrame({
        "Date": pd.date_range("2020-01-01", periods=50, freq="D"),
        "Latitude": 12.97,
        "Longitude": 77.59,
        "Rainfall": np.random.exponential(5, 50),
        "MaxTemp": np.random.uniform(25, 38, 50),
        "MinTemp": np.random.uniform(15, 22, 50),
        "Month": list(range(1, 13)) * 4 + [1, 2],
        "Season": ["Winter", "Summer", "Monsoon", "Post-Monsoon"] * 12 + ["Winter", "Summer"],
        "Monsoon": [0, 0, 1, 0] * 12 + [0, 0],
    })
