from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class BaselineType(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    SEASONAL = "seasonal"
    ROLLING = "rolling"


class AnomalyCategory(StrEnum):
    EXTREME_HIGH = "extreme_high"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    EXTREME_LOW = "extreme_low"


@dataclass
class BaselineRecord:
    baseline_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    location_id: str = ""
    variable: str = ""
    baseline_type: BaselineType = BaselineType.DAILY
    period_start: date = field(default_factory=date.today)
    period_end: date = field(default_factory=date.today)
    mean: float = 0.0
    std: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    p05: float = 0.0
    p25: float = 0.0
    p50: float = 0.0
    p75: float = 0.0
    p95: float = 0.0
    sample_count: int = 0
    valid_years: int = 0
    source: str = ""
    version: str = "1.0.0"
    computed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AnomalyResult:
    location_id: str = ""
    variable: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    current_value: float = 0.0
    baseline_mean: float = 0.0
    baseline_std: float = 0.0
    z_score: float = 0.0
    anomaly_score: float = 0.0
    category: AnomalyCategory = AnomalyCategory.NORMAL
    is_significant: bool = False


@dataclass
class AnomalyReport:
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    location_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    anomalies: list[AnomalyResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)


@dataclass
class BaselineCollection:
    location_id: str = ""
    daily: dict[str, BaselineRecord] = field(default_factory=dict)
    monthly: dict[str, BaselineRecord] = field(default_factory=dict)
    seasonal: dict[str, BaselineRecord] = field(default_factory=dict)
    percentiles: dict[str, BaselineRecord] = field(default_factory=dict)
    version: str = "1.0.0"
    computed_at: datetime = field(default_factory=datetime.utcnow)
