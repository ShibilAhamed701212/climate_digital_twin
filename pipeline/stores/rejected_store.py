from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from pipeline.providers.manager import Observation
from pipeline.stores.observation_store import _observation_to_dict

_logger = logging.getLogger(__name__)


class RejectedStore:
    def __init__(self, base_dir: str | Path = "data/real") -> None:
        self._base_dir = Path(base_dir)
        self._rejected_dir = self._base_dir / "rejected"
        self._rejected_dir.mkdir(parents=True, exist_ok=True)

    def save_batch(self, observations: list[Observation], run_id: str = "") -> int:
        if not observations:
            return 0
        rows = [_observation_to_dict(o) for o in observations]
        df = pd.DataFrame(rows)
        ts = run_id or datetime.now().strftime("%Y%m%dT%H%M%SZ")
        filepath = self._rejected_dir / f"rejected_{ts}.parquet"
        df.to_parquet(filepath, index=False)
        _logger.info("Saved %d rejected observations to %s", len(observations), filepath)
        return len(observations)
