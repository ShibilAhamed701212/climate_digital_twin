"""Digital Twin State Management Package (facade).

Re-exports canonical Digital Twin components from the simulator/ package
for backwards compatibility with BHAI-imported code that references
climatedt.twin.*.
"""

from __future__ import annotations

from simulator.anomaly.detector import AnomalyDetector
from simulator.conflict.resolver import ConflictRecord, ConflictResolver, ResolutionStrategy
from simulator.graph.entity_graph import RelationshipType, TwinEntityGraph
from simulator.historical.computer import BaselineComputer
from simulator.models.baseline import (
    AnomalyReport,
    AnomalyResult,
    BaselineCollection,
    BaselineRecord,
)
from simulator.reconciliation.engine import ReconciliationResult, StateReconciler
from simulator.state_manager.twin_state_manager import TwinStateManager
from simulator.synchronizer.engine import TwinSynchronizer

__all__ = [
    "TwinStateManager",
    "ConflictResolver",
    "ConflictRecord",
    "ResolutionStrategy",
    "StateReconciler",
    "ReconciliationResult",
    "TwinEntityGraph",
    "RelationshipType",
    "BaselineComputer",
    "BaselineCollection",
    "BaselineRecord",
    "AnomalyDetector",
    "AnomalyResult",
    "AnomalyReport",
    "TwinSynchronizer",
]
