# Climate Digital Twin - Facade Package
# This package provides a backward-compatible import shim for BHAI consumers.
# All implementations live in the canonical simulator/, models/, knowledge/, risk/, pipeline/ packages.

from models.registry import ModelRegistry
from simulator.engine.scenario_engine import ScenarioEngine

__all__ = [
    "ScenarioEngine",
    "ModelRegistry",
]
