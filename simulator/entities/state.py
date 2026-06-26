"""State type definitions for the Digital Twin entity model."""

from enum import Enum


class StateType(str, Enum):
    """Enum of valid state types for climate entities."""

    CURRENT = "current"
    HISTORICAL = "historical"
    FORECAST = "forecast"
    SCENARIO = "scenario"


STATE_TYPE_VALUES = {s.value for s in StateType}
