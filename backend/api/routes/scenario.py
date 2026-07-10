from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.dependencies import get_scenario_service
from backend.api.models import (
    CompareScenariosNewRequest,
    CompareScenariosRequest,
    CompareScenariosResponse,
    CreateScenarioRequest,
    CreateScenarioResponse,
    EnsembleSimRequest,
    GenerateFromTemplateRequest,
    MonteCarloRequest,
    MonteCarloSimRequest,
    RunScenarioRequest,
    RunScenarioResponse,
    ScenarioDetailResponse,
    ScenarioGeneratorRequest,
)

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scenario", tags=["Scenario Simulation"])

_scenario_store: dict[str, Any] = {}


@router.post(
    "/create",
    response_model=CreateScenarioResponse,
    summary="Create a scenario definition",
    status_code=status.HTTP_201_CREATED,
)
async def create_scenario(
    request: CreateScenarioRequest,
    scenario_service: Any = Depends(get_scenario_service),  # noqa: B008
) -> CreateScenarioResponse:
    try:
        from datetime import UTC, datetime

        from simulator.models.scenario_models import ScenarioDefinition

        parameters = dict(request.parameters or {})
        parameters.update(
            {
                "location_id": request.location_id,
                "latitude": request.latitude,
                "longitude": request.longitude,
                "duration_days": request.duration_days,
                "temperature_delta": request.temperature_delta,
                "rainfall_multiplier": request.rainfall_multiplier,
                "humidity_delta": request.humidity_delta,
                "wind_speed_delta": request.wind_speed_delta,
                "pressure_delta": request.pressure_delta,
            }
        )

        scenario = ScenarioDefinition(
            scenario_id="",
            name=request.name,
            description=request.description,
            scenario_type=request.scenario_type,
            parameters=parameters,
            created_at=datetime.now(UTC).isoformat(),
        )

        scenario_id = await scenario_service.save_scenario(scenario)
        _scenario_store[scenario_id] = scenario

        return CreateScenarioResponse(
            scenario_id=scenario_id,
            name=scenario.name,
            created_at=scenario.created_at,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Scenario creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scenario creation failed",
        ) from exc


@router.post(
    "/run",
    response_model=RunScenarioResponse,
    summary="Run a scenario simulation",
)
async def run_scenario(
    request: RunScenarioRequest,
    scenario_service: Any = Depends(get_scenario_service),  # noqa: B008
) -> RunScenarioResponse:
    try:
        scenario = await scenario_service.load_scenario(request.scenario_id)
        if scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario '{request.scenario_id}' not found",
            )
        result = await scenario_service.run_scenario(scenario)

        return RunScenarioResponse(
            result_id=getattr(result, "result_id", ""),
            scenario_id=result.scenario_id,
            location_id=result.location_id,
            summary_statistics=result.summary_statistics,
            time_steps=[ts.isoformat() for ts in result.time_steps],
            execution_time_ms=result.execution_time_ms,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Scenario simulation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scenario simulation failed",
        ) from exc


@router.post(
    "/compare",
    response_model=CompareScenariosResponse,
    summary="Compare scenarios",
)
async def compare_scenarios(
    request: CompareScenariosRequest,
    scenario_service: Any = Depends(get_scenario_service),  # noqa: B008
) -> CompareScenariosResponse:
    try:
        scenarios: list[Any] = []
        for sid in request.scenario_ids:
            scenario = await scenario_service.load_scenario(sid)
            if scenario is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Scenario '{sid}' not found",
                )
            scenarios.append(scenario)

        comparisons = await scenario_service.compare_scenarios(scenarios)

        comparison_dicts: list[dict[str, Any]] = []
        for comp in comparisons:
            comparison_dicts.append(
                {
                    "comparison_id": getattr(comp, "comparison_id", ""),
                    "baseline_result_id": comp.baseline_result_id,
                    "scenario_result_id": comp.scenario_result_id,
                    "variable_deltas": comp.variable_deltas,
                    "percentage_changes": comp.percentage_changes,
                    "significant_variables": comp.significant_variables,
                    "summary": comp.summary,
                }
            )

        return CompareScenariosResponse(
            comparisons=comparison_dicts,
            total_comparisons=len(comparison_dicts),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Scenario comparison failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scenario comparison failed",
        ) from exc


@router.post(
    "/monte-carlo",
    summary="Run Monte Carlo simulation",
)
async def run_monte_carlo(
    request: MonteCarloRequest,
    scenario_service: Any = Depends(get_scenario_service),  # noqa: B008
) -> dict[str, Any]:
    try:
        scenario = await scenario_service.load_scenario(request.scenario_id)
        if scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario '{request.scenario_id}' not found",
            )
        mc_result = await scenario_service.run_monte_carlo_scenario(
            scenario=scenario,
            distributions=request.distributions,
        )

        return {
            "scenario_id": request.scenario_id,
            "num_samples": getattr(mc_result, "num_samples", 0),
            "statistics": getattr(mc_result, "statistics", {}),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _logger.exception("Monte Carlo simulation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Monte Carlo simulation failed",
        ) from exc


@router.get(
    "/templates",
    summary="List scenario templates",
)
async def list_templates() -> dict[str, list[dict[str, Any]]]:
    templates = [
        {
            "name": "warming_1_5",
            "display_name": "+1.5\u00b0C Warming",
            "description": "Moderate warming scenario (+1.5\u00b0C)",
            "type": "temperature",
        },
        {
            "name": "warming_2_0",
            "display_name": "+2.0\u00b0C Warming",
            "description": "Significant warming scenario (+2.0\u00b0C)",
            "type": "temperature",
        },
        {
            "name": "warming_3_0",
            "display_name": "+3.0\u00b0C Warming",
            "description": "Extreme warming scenario (+3.0\u00b0C)",
            "type": "temperature",
        },
        {
            "name": "rainfall_plus_20",
            "display_name": "+20% Rainfall",
            "description": "Increased rainfall scenario (+20%)",
            "type": "rainfall",
        },
        {
            "name": "rainfall_minus_20",
            "display_name": "-20% Rainfall",
            "description": "Decreased rainfall scenario (-20%)",
            "type": "rainfall",
        },
        {
            "name": "extreme",
            "display_name": "Extreme Worst-Case",
            "description": "Extreme scenario (+4\u00b0C, +30% rainfall)",
            "type": "extreme_event",
        },
        {
            "name": "drought",
            "display_name": "Drought Conditions",
            "description": "Drought scenario (+2\u00b0C, -20% rainfall)",
            "type": "extreme_event",
        },
        {
            "name": "ssp585_2050",
            "display_name": "IPCC SSP5-8.5 (2050)",
            "description": "IPCC worst-case emissions pathway for 2050",
            "type": "ipcc",
        },
        {
            "name": "ssp245_2050",
            "display_name": "IPCC SSP2-4.5 (2050)",
            "description": "IPCC intermediate emissions pathway for 2050",
            "type": "ipcc",
        },
    ]
    return {"templates": templates}


@router.post(
    "/generate/{template}",
    summary="Generate scenario from template",
    status_code=status.HTTP_201_CREATED,
)
async def generate_from_template(
    template: str,
    request: GenerateFromTemplateRequest,
    scenario_service: Any = Depends(get_scenario_service),  # noqa: B008
) -> dict[str, Any]:
    try:
        generator = scenario_service.generator

        template_map: dict[str, Any] = {
            "warming_1_5": lambda: generator.warming_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                1.5,
                request.duration_days or 30,
            ),
            "warming_2_0": lambda: generator.warming_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                2.0,
                request.duration_days or 30,
            ),
            "warming_3_0": lambda: generator.warming_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                3.0,
                request.duration_days or 30,
            ),
            "rainfall_plus_20": lambda: generator.rainfall_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                1.2,
                request.duration_days or 30,
            ),
            "rainfall_minus_20": lambda: generator.rainfall_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                0.8,
                request.duration_days or 30,
            ),
            "extreme": lambda: generator.extreme_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                request.duration_days or 30,
            ),
            "drought": lambda: generator.drought_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                request.duration_days or 90,
            ),
            "ssp585_2050": lambda: generator.ipcc_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                "ssp585",
                2050,
            ),
            "ssp245_2050": lambda: generator.ipcc_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                "ssp245",
                2050,
            ),
        }

        if template not in template_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template}' not found. Available: {list(template_map.keys())}",
            )

        scenario = template_map[template]()
        scenario_id = await scenario_service.save_scenario(scenario)

        raw_type = scenario.scenario_type
        scenario_type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type)

        return {
            "scenario_id": scenario_id,
            "name": scenario.name,
            "description": scenario.description,
            "scenario_type": scenario_type_str,
            "template": template,
            "created_at": scenario.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("Template generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template generation failed",
        ) from exc


# ---------------------------------------------------------------------------
# Helpers for the new scenario extension endpoints
# ---------------------------------------------------------------------------


def _build_base_observations(base_params: dict[str, Any]) -> list:
    """Build WeatherObservation list from request base_params."""
    import math as _math

    from simulator.models.weather import DataSource, QualityFlag, WeatherObservation

    location_id = base_params.get("location_id", "unknown")
    latitude = base_params.get("latitude", 12.97)
    longitude = base_params.get("longitude", 77.59)
    hours = base_params.get("hours", 24)
    start_temp = base_params.get("temperature_2m", 25.0)

    obs_list: list[WeatherObservation] = []
    for h in range(hours):
        obs_list.append(
            WeatherObservation(
                location_id=location_id,
                latitude=latitude,
                longitude=longitude,
                timestamp=datetime.now(UTC) + timedelta(hours=h),
                temperature_2m=round(start_temp + 2 * _math.sin(2 * _math.pi * h / 24), 2),
                precipitation_mm=base_params.get("precipitation_mm", 0.0),
                humidity_pct=base_params.get("humidity_pct", 60.0),
                pressure_hpa=base_params.get("pressure_hpa", 1013.0),
                wind_speed_10m=base_params.get("wind_speed_10m", 5.0),
                wind_direction_10m=base_params.get("wind_direction_10m", 180.0),
                data_source=DataSource.SYNTHETIC,
                quality_flag=QualityFlag.ESTIMATED,
            )
        )
    return obs_list


def _build_scenario_def(
    scenario_type: str,
    params: dict[str, Any],
    name: str = "API Scenario",
    description: str = "",
) -> Any:
    """Build a ScenarioDefinition from API request parameters."""
    from simulator.models.scenario_models import ScenarioDefinition

    return ScenarioDefinition(
        scenario_id=f"api_{uuid.uuid4().hex[:8]}",
        name=name,
        description=description or f"API-generated {scenario_type} scenario",
        scenario_type=scenario_type,
        parameters={k: v for k, v in params.items() if isinstance(v, (int, float, str))},
    )


# ---------------------------------------------------------------------------
# 1. Monte Carlo simulation using MonteCarloEngine
# ---------------------------------------------------------------------------


@router.post(
    "/monte-carlo-sim",
    summary="Run Monte Carlo simulation using probabilistic engine",
)
async def run_monte_carlo_simulation(
    request: MonteCarloSimRequest,
) -> dict[str, Any]:
    try:
        from simulator.engine.monte_carlo import MonteCarloEngine
        from simulator.engine.perturbation import PerturbationEngine

        perturbation = PerturbationEngine(pattern="constant")
        mc_engine = MonteCarloEngine(
            perturbation_engine=perturbation,
            n_samples=request.num_simulations,
            random_seed=42,
        )

        base_obs = _build_base_observations(request.base_params)
        scenario = _build_scenario_def(
            scenario_type=request.scenario_type,
            params=request.base_params,
            name=f"MC {request.scenario_type}",
        )

        distributions = dict(request.distributions) if request.distributions else {}

        result = await mc_engine.run_monte_carlo(
            base_data=base_obs,
            scenario_template=scenario,
            parameter_distributions=distributions,
        )

        return {
            "n_samples": result.n_samples,
            "summary": result.summary,
            "confidence_intervals": result.confidence_intervals,
            "sensitivity": result.sensitivity,
            "config": {
                "num_simulations": request.num_simulations,
                "confidence_level": request.confidence_level,
                "scenario_type": request.scenario_type,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        _logger.exception("Monte Carlo simulation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Monte Carlo simulation failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# 2. Compare scenarios using SimulationComparison
# ---------------------------------------------------------------------------


@router.post(
    "/compare-scenarios",
    summary="Compare multiple scenarios using SimulationComparison engine",
)
async def compare_scenarios_new(
    request: CompareScenariosNewRequest,
) -> dict[str, Any]:
    try:
        from simulator.engine.perturbation import PerturbationEngine
        from simulator.scenarios.comparison import ScenarioComparison

        engine = PerturbationEngine(pattern="constant")
        comparator = ScenarioComparison()

        base_params_list = request.scenarios
        baseline_idx = request.baseline_index

        # Build scenario definitions
        built_scenarios: list[Any] = []
        for _i, cfg in enumerate(base_params_list):
            s = _build_scenario_def(
                scenario_type=cfg.scenario_type,
                params=cfg.parameters,
                name=cfg.name,
            )
            built_scenarios.append(s)

        # Build dummy base observations and run simulations
        base_obs = _build_base_observations(
            {
                "location_id": request.scenarios[0].location_id,
            }
        )

        from simulator.models.scenario_models import SimulationResult

        simulated: list[SimulationResult] = []
        for sc in built_scenarios:
            perturbed = engine.apply_perturbation(base_obs, sc)
            time_series: dict[str, list[float]] = {
                "temperature_2m": [o.temperature_2m for o in perturbed],
                "precipitation_mm": [o.precipitation_mm for o in perturbed],
                "humidity_pct": [o.humidity_pct for o in perturbed],
                "pressure_hpa": [o.pressure_hpa for o in perturbed],
                "wind_speed_10m": [o.wind_speed_10m for o in perturbed],
            }
            simulated.append(
                SimulationResult(
                    location_id=sc.parameters.get("location_id", "unknown"),
                    scenario_id=sc.scenario_id,
                    timestamp=datetime.now(UTC).isoformat(),
                    baseline={"data_source": "api_compare_baseline"},
                    simulated={"time_series": time_series},
                    deltas={},
                    duration_ms=0.0,
                    success=True,
                )
            )

        # Perform comparisons
        if baseline_idx >= len(simulated):
            baseline_idx = 0
        baseline = simulated[baseline_idx]

        comparisons: list[dict[str, Any]] = []
        for i, sim in enumerate(simulated):
            if i == baseline_idx:
                continue
            comp = comparator.compare_baseline_scenario(baseline, sim)
            comparisons.append(
                {
                    "comparison_id": comp.comparison_id,
                    "scenario_a": built_scenarios[baseline_idx].name,
                    "scenario_b": built_scenarios[i].name,
                    "variable_deltas": comp.variable_deltas,
                    "percentage_changes": comp.percentage_changes,
                    "significant_variables": comp.significant_variables,
                    "summary": comp.summary,
                }
            )

        _report = {}

        return {
            "comparisons": comparisons,
            "total_comparisons": len(comparisons),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        _logger.exception("Scenario comparison failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario comparison failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# 3. Ensemble simulation using EnsembleSimulator
# ---------------------------------------------------------------------------


@router.post(
    "/ensemble",
    summary="Run ensemble simulation across multiple scenarios",
)
async def run_ensemble(
    request: EnsembleSimRequest,
) -> dict[str, Any]:
    try:
        from simulator.engine.perturbation import PerturbationEngine
        from simulator.scenarios.ensemble import EnsembleSimulator

        engine = PerturbationEngine(pattern="constant")
        ensemble = EnsembleSimulator(
            perturbation_engine=engine,
            n_members=max(len(request.members), 1),
        )

        base_obs = _build_base_observations({"location_id": request.location_id})
        base_scenario = _build_scenario_def(
            scenario_type=request.members[0].config.scenario_type
            if request.members
            else "temperature",
            params=request.members[0].config.parameters if request.members else {},
            name=request.members[0].config.name if request.members else "Ensemble Base",
        )

        result = await ensemble.run_ensemble(
            base_data=base_obs,
            base_scenario=base_scenario,
        )

        return {
            "n_members": result.n_members,
            "ensemble_mean": result.ensemble_mean,
            "ensemble_spread": result.ensemble_spread,
            "member_rankings": result.member_rankings,
            "summary": result.summary,
            "config": {
                "n_members": len(request.members),
                "location_id": request.location_id,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        _logger.exception("Ensemble simulation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ensemble simulation failed: {exc}",
        ) from exc


# ---------------------------------------------------------------------------
# 4. Generate scenario using ScenarioGenerator
# ---------------------------------------------------------------------------


@router.post(
    "/scenario-generator",
    summary="Generate scenario projections using ScenarioGenerator",
    status_code=status.HTTP_201_CREATED,
)
async def generate_scenario(
    request: ScenarioGeneratorRequest,
) -> dict[str, Any]:
    try:
        from simulator.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator()
        params = dict(request.parameters)

        scenario_type = request.scenario_type.lower()

        if scenario_type == "temperature":
            delta = params.get("temperature_delta", 2.0)
            scenario = generator.warming_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                float(delta),
                request.duration_days,
            )
        elif scenario_type == "rainfall":
            mult = params.get("rainfall_multiplier", 1.2)
            scenario = generator.rainfall_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                float(mult),
                request.duration_days,
            )
        elif scenario_type in ("extreme", "extreme_event"):
            scenario = generator.extreme_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                request.duration_days,
            )
        elif scenario_type == "drought":
            scenario = generator.drought_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                request.duration_days,
            )
        elif scenario_type in ("ipcc", "ssp"):
            pathway = params.get("pathway", "ssp245")
            target_year = int(params.get("target_year", 2050))
            scenario = generator.ipcc_scenario(
                request.location_id,
                request.latitude,
                request.longitude,
                str(pathway),
                target_year,
            )
        else:
            scenario = generator.custom_scenario(
                name=params.get("name", f"Custom {scenario_type}"),
                description=params.get("description", f"Custom {scenario_type} scenario"),
                location_id=request.location_id,
                latitude=request.latitude,
                longitude=request.longitude,
                parameters=params,
                duration_days=request.duration_days,
            )

        issues = generator.validate_scenario(scenario)
        raw_type = scenario.scenario_type
        scenario_type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type)

        return {
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "description": scenario.description,
            "scenario_type": scenario_type_str,
            "parameters": dict(scenario.parameters),
            "validation_issues": issues,
            "created_at": scenario.created_at,
        }
    except Exception as exc:
        _logger.exception("Scenario generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario generation failed: {exc}",
        ) from exc


@router.get(
    "/{scenario_id}",
    response_model=ScenarioDetailResponse,
    summary="Get scenario details",
)
async def get_scenario(
    scenario_id: str,
    scenario_service: Any = Depends(get_scenario_service),  # noqa: B008
) -> ScenarioDetailResponse:
    try:
        scenario = await scenario_service.load_scenario(scenario_id)
        if scenario is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario '{scenario_id}' not found",
            )
        raw_type = scenario.scenario_type
        scenario_type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type)

        return ScenarioDetailResponse(
            scenario_id=scenario.scenario_id,
            name=scenario.name,
            description=scenario.description,
            scenario_type=scenario_type_str,
            location_id=scenario.location_id,
            duration_days=scenario.duration_days,
            parameters=scenario.parameters,
        )
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("Scenario retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scenario retrieval failed",
        ) from exc
