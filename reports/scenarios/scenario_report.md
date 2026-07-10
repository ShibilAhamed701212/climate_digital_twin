# Scenario Simulation Report

## Overview
The Scenario Engine enables what-if climate simulations. Users can adjust temperature, rainfall, monsoon patterns, and extreme events to understand potential climate impacts on Karnataka. The engine supports preset and custom scenarios with deterministic simulation.

## Architecture

### Components

| Component | File | Responsibility |
|-----------|------|----------------|
| ScenarioEngine | `simulator/engine/scenario_engine.py` | Core simulation execution — applies scenario parameters to baseline data |
| ScenarioService | `simulator/services/scenario_service.py` | Integration layer — connects twin, creates/manages scenarios, runs simulations |
| ScenarioBuilder | `simulator/scenarios/scenario_builder.py` | Factory for scenario definitions (preset + custom) |
| ScenarioValidator | `simulator/validators/scenario_validator.py` | Parameter validation |
| Scenario API | `simulator/scenarios/api.py` | REST API (6 endpoints) |

### Scenario Types

| Type | Parameters | Description |
|------|------------|-------------|
| temperature | temperature_delta | Uniform temperature adjustment |
| rainfall | rainfall_change_pct | Percentage change in rainfall |
| monsoon | delay_days, intensity_reduction_pct | Monsoon timing & intensity |
| extreme_event | event_type, temperature_delta, rainfall_change_pct | Heatwave, flood, or drought |
| combined | scenarios (list) | Multiple sub-scenarios applied together |

### Preset Scenarios (11 total)

| ID | Name | Type | Delta |
|----|------|------|-------|
| temp_plus_1 | Temperature +1°C | temperature | +1.0°C |
| temp_plus_2 | Temperature +2°C | temperature | +2.0°C |
| temp_minus_1 | Temperature -1°C | temperature | -1.0°C |
| rain_plus_10 | Rainfall +10% | rainfall | +10% |
| rain_plus_40 | Rainfall +40% | rainfall | +40% |
| rain_minus_25 | Rainfall -25% | rainfall | -25% |
| monsoon_delayed_15 | Monsoon Delayed 15 Days | monsoon | +15 days delay, -20% intensity |
| monsoon_early_7 | Monsoon Early 7 Days | monsoon | -7 days delay |
| heatwave | Extreme Heat Wave | extreme_event | +5.0°C, 7 days |
| flood | Flood Scenario | extreme_event | +200% rain, 5 days |
| drought | Drought Condition | extreme_event | -80% rain, 30 days |

## API Endpoints

### Scenario Engine API (`:8002`)

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Service health check |
| POST | /scenarios/create | Create a new scenario definition |
| POST | /scenarios/simulate | Run a scenario simulation |
| GET | /scenarios | List all scenarios (preset + custom) |
| GET | /scenarios/{id}/compare | Compare simulation with baseline |
| POST | /scenarios/validate | Validate scenario parameters |
| DELETE | /scenarios/{id} | Delete a custom scenario |

### Simulation Flow

```
POST /scenarios/simulate
  → ScenarioService.run_simulation(scenario_id, location_ids)
    → _collect_baseline(location_ids)  # from twin state
    → ScenarioEngine.run_simulation(scenario, baseline)
      → for each location: _simulate_single(scenario, baseline)
        → _apply_modifications(temperature|rainfall|monsoon|extreme_event|combined)
        → _compute_deltas()
        → return SimulationResult
    → apply results back to twin
    → return ScenarioRun
```

## Configuration

From `simulator/configs/scenario.yaml`:

| Parameter | Value | Description |
|-----------|-------|-------------|
| temperature.min_delta | -5.0 | Min temperature adjustment |
| temperature.max_delta | 5.0 | Max temperature adjustment |
| temperature.step | 0.5 | Temperature step size |
| rainfall.min_percent_change | -100.0 | Min rainfall change |
| rainfall.max_percent_change | 500.0 | Max rainfall change |
| rainfall.step | 5.0 | Rainfall step size |
| monsoon.max_delay_days | 30 | Max monsoon delay |
| monsoon.max_advance_days | 15 | Max monsoon advance |
| extreme_events | enabled | flood, heatwave, drought |
| validation.max_combined_scenarios | 5 | Max combined sub-scenarios |
| simulation.deterministic | true | Deterministic mode (seed=42) |
| simulation.max_execution_ms | 3000 | Max simulation time |
| output.formats | [json, csv, markdown] | Output formats |

## Scenario Model

```python
ScenarioDefinition:
  scenario_id: str
  name: str
  description: str
  scenario_type: str
  parameters: dict

ScenarioRun:
  run_id: str
  scenario: ScenarioDefinition
  results: list[SimulationResult]
  started_at: str
  completed_at: str
  total_duration_ms: float
  location_count: int
  status: str

SimulationResult:
  location_id: str
  scenario_id: str
  timestamp: str
  baseline: dict
  simulated: dict
  deltas: dict
  duration_ms: float
  success: bool
  error_message: str (if failed)
```

## Performance

- Single location simulation: <1ms
- Full district simulation (30 locations): ~5ms
- Max 3s timeout enforced by config
- Deterministic mode ensures reproducible results

## Example Usage

```python
# Create a custom scenario
POST /scenarios/create
{
  "scenario_id": "my_scenario",
  "name": "Bangalore +3°C",
  "description": "3-degree warming for Bangalore",
  "scenario_type": "temperature",
  "parameters": {"temperature_delta": 3.0}
}

# Simulate
POST /scenarios/simulate
{
  "scenario_id": "my_scenario",
  "location_ids": ["KA-BLR-001"]
}

# Response
{
  "run_id": "run_a1b2c3d4e5f6",
  "scenario": {...},
  "results": [{
    "location_id": "KA-BLR-001",
    "baseline": {"rainfall": 85.3, "max_temp": 32.1, ...},
    "simulated": {"rainfall": 85.3, "max_temp": 35.1, ...},
    "deltas": {"max_temp": 3.0},
    "success": true,
    "duration_ms": 0.35
  }],
  "location_count": 1,
  "status": "completed",
  "total_duration_ms": 0.42
}
```

## Limitations

1. Scenarios are not persisted across restarts (in-memory storage)
2. Preset scenarios cannot be modified (re-create as custom)
3. Combined scenarios limited to 5 sub-scenarios
4. No spatial interpolation between grid cells
5. Default locations (KA-BLR-001, KA-MYS-001, KA-BEL-001) used when no twin data exists
