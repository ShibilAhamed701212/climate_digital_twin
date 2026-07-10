from typing import Any


class FeedbackStore:
    def __init__(self) -> None:
        self._records: list[Any] = []

    def save(self, record: Any) -> None:
        self._records.append(record)

    def list_all(self) -> list[Any]:
        return self._records
