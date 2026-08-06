"""HazardStore — JSONL persistence for HazardAssessment records.

Supports append/history, latest by location/hazard/type, lookup by ID,
restart recovery, and idempotency.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from risk.models.hazard import AssessmentType, HazardAssessment


class HazardStore:
    def __init__(self, path: str = "data/hazard/assessments.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: dict[str, HazardAssessment] | None = None

    def save(self, assessment: HazardAssessment) -> None:
        with self._lock:
            with open(self._path, "a") as f:
                f.write(json.dumps(assessment.to_dict()) + "\n")
            if self._cache is not None:
                self._cache[assessment.assessment_id] = assessment

    def _load_all(self) -> dict[str, HazardAssessment]:
        if self._cache is not None:
            return self._cache
        if not self._path.exists():
            self._cache = {}
            return self._cache
        result: dict[str, HazardAssessment] = {}
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        a = HazardAssessment.from_dict(json.loads(line))
                        result[a.assessment_id] = a
                    except Exception:
                        continue
        self._cache = result
        return result

    def get(self, assessment_id: str) -> HazardAssessment | None:
        return self._load_all().get(assessment_id)

    def list_recent(self, limit: int = 20) -> list[HazardAssessment]:
        all_a = list(self._load_all().values())
        all_a.sort(key=lambda a: a.generated_at, reverse=True)
        return all_a[:limit]

    def list_by_location(self, location_id: str, limit: int = 50) -> list[HazardAssessment]:
        matched = [a for a in self._load_all().values() if a.location_id == location_id]
        matched.sort(key=lambda a: a.generated_at, reverse=True)
        return matched[:limit]

    def latest_by_location(
        self,
        location_id: str,
        hazard_type: str | None = None,
        assessment_type: AssessmentType | None = None,
    ) -> HazardAssessment | None:
        candidates = self._load_all().values()
        filtered = [
            a
            for a in candidates
            if a.location_id == location_id
            and (hazard_type is None or a.hazard_type == hazard_type)
            and (assessment_type is None or a.assessment_type == assessment_type)
        ]
        if not filtered:
            return None
        filtered.sort(key=lambda a: a.generated_at, reverse=True)
        return filtered[0]

    def count(self) -> int:
        return len(self._load_all())

    def clear(self) -> None:
        with self._lock:
            self._cache = {}
            if self._path.exists():
                self._path.unlink()
