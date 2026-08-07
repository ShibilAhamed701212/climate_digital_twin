class ScenarioType:
    TEMPERATURE = "temperature"
    RAINFALL = "rainfall"
    MONSOON = "monsoon"
    EXTREME_EVENT = "extreme_event"
    COMBINED = "combined"

    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    def __str__(self) -> str:
        return self._value
