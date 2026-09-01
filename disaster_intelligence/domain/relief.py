from __future__ import annotations

from typing import Any

from disaster_intelligence.domain.entities import ReliefPlan
from disaster_intelligence.domain.ids import ulid


def score_zones(
    zonal_rows: list[dict[str, Any]],
    hospitals_by_location: dict[str, int],
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for row in zonal_rows:
        loc = str(row.get("location_id") or "")
        flood = float(row.get("flood_fraction") or 0.0)
        pop = row.get("pop_exposed_est")
        pop_term = 0.0 if pop is None else min(1.0, float(pop) / 100000.0)
        hosp = hospitals_by_location.get(loc, 0)
        hosp_term = min(1.0, hosp / 3.0)
        score = (
            weights.get("pop", 0.4) * pop_term
            + weights.get("flood_frac", 0.4) * flood
            + weights.get("hospitals_hit", 0.2) * hosp_term
        )
        reasons = []
        if flood > 0:
            reasons.append(f"observed_inundation_fraction={flood:.3f}")
        if pop is None:
            reasons.append("population_unavailable")
        else:
            reasons.append(f"pop_exposed_est={pop}")
        if hosp:
            reasons.append(f"hospitals_in_water={hosp}")
        scored.append(
            {
                "zone_id": loc or ulid(),
                "location_id": loc,
                "score": round(score, 4),
                "rank": 0,
                "reasons": reasons,
            }
        )
    scored.sort(key=lambda z: z["score"], reverse=True)
    for idx, zone in enumerate(scored, start=1):
        zone["rank"] = idx
    return scored


def build_relief_plan(
    assessment_id: str,
    zonal_rows: list[dict[str, Any]],
    hospitals_by_location: dict[str, int],
    weights: dict[str, float],
) -> ReliefPlan:
    return ReliefPlan(
        plan_id=ulid(),
        assessment_id=assessment_id,
        zones=score_zones(zonal_rows, hospitals_by_location, weights),
    )
