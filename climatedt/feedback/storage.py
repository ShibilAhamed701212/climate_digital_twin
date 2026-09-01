"""In-memory + JSONL-persistent feedback storage."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FEEDBACK_DIR = Path(os.environ.get("FEEDBACK_DATA_DIR", "data/feedback"))
_JSONL_PATH = _FEEDBACK_DIR / "feedback.jsonl"


class FeedbackStore:
    """Stores feedback records in memory and optionally persists to JSONL."""

    def __init__(self, persist: bool = True) -> None:
        self._records: list[Any] = []
        self._persist = persist
        if persist:
            self._load()

    def _load(self) -> None:
        if not _JSONL_PATH.exists():
            return
        try:
            with open(_JSONL_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        self._records.append(_dict_to_record(data))
                    except (json.JSONDecodeError, Exception) as exc:
                        logger.debug("Skipping bad feedback line: %s", exc)
        except Exception as exc:
            logger.warning("Could not load feedback store: %s", exc)

    def save(self, record: Any) -> None:
        self._records.append(record)
        if self._persist:
            self._append_jsonl(record)

    def _append_jsonl(self, record: Any) -> None:
        try:
            _FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
            row = _record_to_dict(record)
            with open(_JSONL_PATH, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
        except Exception as exc:
            logger.warning("Could not persist feedback: %s", exc)

    def list_all(self) -> list[Any]:
        return self._records


def _record_to_dict(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        return record.to_dict()
    if hasattr(record, "__dict__"):
        return {k: v for k, v in record.__dict__.items() if not k.startswith("_")}
    return {"rating": getattr(record, "rating", 0), "comment": ""}


def _dict_to_record(data: dict[str, Any]) -> Any:
    """Reconstruct a CapturedFeedback from a dict."""
    from climatedt.feedback.capture import CapturedFeedback

    return CapturedFeedback(
        record_id=data.get("record_id", ""),
        status=data.get("status", "captured"),
        feedback_type=data.get("feedback_type", "general"),
        location_id=data.get("location_id", ""),
        rating=float(data.get("rating", 0) or 0),
        comment=data.get("comment", ""),
        reference_id=data.get("reference_id", ""),
        created_at=data.get("created_at", ""),
    )
