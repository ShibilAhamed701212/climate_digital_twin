"""Phase 7 — Versioned, sourced simulation parameters.

Every parameter carries an explicit scientific source/basis so the parameter
choice is auditable (DoD: "all parameters versioned and sourced").  The
default set is for Bengaluru (12.97 N, 77.59 E) — an inland, semi-arid
location — using documented typical values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

METHOD = "coupled-water-balance"
METHOD_VERSION = "1.0.0"
CONFIG_VERSION = "2026-07-31"

SIMULATED_AUTHENTICITY = "SIMULATED"


@dataclass(frozen=True)
class SimulationParameters:
    """Versioned parameter set for the coupled land-surface simulation."""

    # Location.
    location_id: str = "bengaluru"
    latitude: float = 12.97
    longitude: float = 77.59

    # Soil water bucket (plant-available water).
    # capacity_mm: field capacity minus wilting point integrated over the
    #   root zone.  ~150 mm/m is a typical published value for the plant-
    #   available water of a loamy root zone (FAO-56 Ch. 8, Table 19/22 range).
    capacity_mm: float = 150.0
    # depletion_fraction p: fraction of available water below which
    #   evapotranspiration is linearly stressed (FAO-56 Ch. 8, Table 22).
    depletion_fraction: float = 0.5
    # initial_storage_mm: documented warm-start.  Not a "magic 50%" default
    #   for physical spin-up — a 3-month spin-up runs before results are
    #   reported, and the initial condition is always recorded verbatim.
    initial_storage_mm: float = 75.0

    # SCS Curve Number (AMC II, normal).  A mid-range value for the mixed
    #   semi-urban / agricultural land surface of the Bengaluru region
    #   (USDA TR-55 Table 2-2).
    cn_ii: float = 70.0

    # Hargreaves-Samani coefficient.  0.0023 interior, 0.0019 coastal
    #   (FAO-56 Ch. 4).  Bengaluru is inland Karnataka -> 0.0023.
    krs: float = 0.0023

    config_version: str = CONFIG_VERSION
    method: str = METHOD
    method_version: str = METHOD_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "capacity_mm": self.capacity_mm,
            "depletion_fraction": self.depletion_fraction,
            "initial_storage_mm": self.initial_storage_mm,
            "cn_ii": self.cn_ii,
            "krs": self.krs,
            "config_version": self.config_version,
            "method": self.method,
            "method_version": self.method_version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationParameters":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def parameter_sources(self) -> dict[str, str]:
        """Documented basis for each parameter (audit trail)."""
        return {
            "capacity_mm": (
                "FAO-56 Ch.8: ~150 mm plant-available water per metre of "
                "loamy root zone (typical published range 100-200)."
            ),
            "depletion_fraction": ("FAO-56 Ch.8 Table 22: p=0.5 general / deep-rooted crops."),
            "initial_storage_mm": (
                "Documented warm-start; results reported after 3-month "
                "spin-up, initial condition stored verbatim in provenance."
            ),
            "cn_ii": (
                "USDA TR-55 Table 2-2: mid-range CN for mixed "
                "semi-urban/agricultural land use (pervious, good condition)."
            ),
            "krs": (
                "FAO-56 Ch.4: kRS=0.0023 for interior regions (Bengaluru is inland Karnataka)."
            ),
        }
