# Digital Twin Engine

## Overview

The **Digital Twin Engine** manages the dynamic, spatial representation of regional climate states across India (with focused calibration for Karnataka). It maintains versioned, observable entity states, synchronizes real-time weather observations, reconciles simulated states with historical data, and supports coupled physical subprocesses.

---

## Core Components

### 1. Versioned State Manager (`VersionedStateStore` / `StateManager`)
- Maintains full state lineage for every monitored location.
- Implements transaction-safe version creation, historical rollback, and point-in-time state queries.
- Guarantees thread-safe atomic updates.

### 2. Coupled Simulation Engine (`CoupledSimulationEngine`)
Runs physics-informed hydro-meteorological processes:
- **Penman-Monteith Evapotranspiration (`penman_monteith.py`)**: Computes reference evapotranspiration ($ET_0$) using daily solar radiation, air temperature, wind speed, and relative humidity.
- **SCS Curve Number Runoff (`runoff.py`)**: Estimates surface runoff based on soil hydrologic group and antecedent moisture conditions.
- **Soil Water Balance (`soil_water.py`)**: Models multi-layer root-zone soil water content, infiltration, and percolation.
- **SPEI Drought Classifier (`drought.py`)**: Standardized Precipitation-Evapotranspiration Index calculation over 1, 3, 6, and 12-month timescales.

### 3. Spatial Grid Twin (`GridTwin`)
- Divides geographic regions into spatial grid cells (e.g., 0.25° x 0.25° resolution).
- Performs spatial interpolation (IDW / Nearest Neighbor) across sensor observation points.
- Enables spatial anomaly detection and grid-level simulation.

### 4. Real-time Synchronizer (`TwinSyncService`)
- Listens for new weather observations from the ingestion pipeline.
- Performs authenticity checks, data quality verification, and out-of-order sequence resolution.
- Merges incoming data into the active twin state.

---

## State Schema (`ClimateEntity` / `TwinState`)

```json
{
  "location_id": "KA-BLR-001",
  "latitude": 12.97,
  "longitude": 77.59,
  "district": "Bengaluru Urban",
  "timestamp": "2026-08-07T00:00:00Z",
  "max_temp": 32.5,
  "min_temp": 22.1,
  "rainfall": 12.3,
  "humidity": 68.0,
  "wind_speed": 4.2,
  "solar_radiation": 18.5,
  "soil_moisture": 0.32,
  "version": 42,
  "quality_flag": "VALIDATED"
}
```

---

## Python API Usage

```python
from simulator.state_manager.manager import StateManager
from simulator.entities.climate_entity import ClimateEntity

manager = StateManager()

# Create initial state
entity = ClimateEntity(
    location_id="KA-BLR-001",
    latitude=12.97,
    longitude=77.59,
    max_temp=31.0,
    min_temp=21.5,
    rainfall=5.0
)
v1 = manager.create_version(entity)

# Update observation
updated_entity = entity.update_state(max_temp=33.2, rainfall=15.0)
v2 = manager.create_version(updated_entity)

# Query history
history = manager.get_history("KA-BLR-001")
```
