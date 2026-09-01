from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from disaster_intelligence.application.container import AppContainer
from disaster_intelligence.application.preprocess import write_geoparquet_sidecar
from disaster_intelligence.config import env_flag
from disaster_intelligence.domain.entities import Assessment
from disaster_intelligence.domain.enums import QualityFlag
from disaster_intelligence.domain.geometry import line_length_km
from disaster_intelligence.domain.ids import ulid
from disaster_intelligence.domain.intersect import intersect_osm
from disaster_intelligence.domain.relief import build_relief_plan
from disaster_intelligence.domain.zonal import (
    geometry_centroid,
    location_id_containing,
    zonal_stats,
)


def _pixel_area_km2(bounds: dict[str, float], width: int, height: int) -> float:
    if width <= 0 or height <= 0:
        return 0.0
    deg_lat = abs(bounds["north"] - bounds["south"]) / height
    deg_lon = abs(bounds["east"] - bounds["west"]) / width
    # Approximate at 15°N: 1 deg lat ~ 110.9 km, lon ~ 107.2 km
    return (deg_lat * 110.9) * (deg_lon * 107.2)


def _load_locations(path: str) -> list[dict[str, Any]]:
    file = Path(path)
    if not file.exists():
        return []
    data = json.loads(file.read_text(encoding="utf-8"))
    return list(data.get("features") or [])


def run_assessment(
    container: AppContainer,
    *,
    event_id: str,
    job_id: str,
    mask: list[list[int]],
    bounds: dict[str, float],
    authenticity: str,
    quality_flags: list[str],
    confidence_mean: float | None = None,
    model_cards: dict[str, str] | None = None,
) -> Assessment:
    event = container.events.get(event_id)
    assert event is not None
    osm = container.osm.load(event.aoi)
    buildings = intersect_osm(osm.get("buildings") or [], mask, bounds)
    roads = intersect_osm(osm.get("roads") or [], mask, bounds)
    amenities = intersect_osm(osm.get("amenities") or [], mask, bounds)

    loc_path = str(container.config.get("location_map_file") or "config/aoi/location_ids.geojson")
    locations = _load_locations(loc_path)
    height = len(mask)
    width = len(mask[0]) if mask else 0
    zonal = zonal_stats(locations, mask, bounds, _pixel_area_km2(bounds, width, height))

    b_in = sum(1 for f in buildings if f["properties"].get("in_water"))
    r_in = [f for f in roads if f["properties"].get("in_water")]
    road_km_parts = [line_length_km(f.get("geometry") or {}) for f in r_in]
    road_km_known = [x for x in road_km_parts if x is not None]
    hospitals = [
        f
        for f in amenities
        if f["properties"].get("in_water")
        and str(f["properties"].get("amenity") or "") == "hospital"
    ]
    schools = [
        f
        for f in amenities
        if f["properties"].get("in_water") and str(f["properties"].get("amenity") or "") == "school"
    ]
    water_pixels = sum(1 for row in mask for v in row if v > 0)
    flood_area = round(water_pixels * _pixel_area_km2(bounds, width, height), 4)
    pop_values = [z["pop_exposed_est"] for z in zonal if z.get("pop_exposed_est") is not None]
    flags = list(quality_flags)
    flags.append(QualityFlag.INUNDATION_PROXY_NOT_STRUCTURAL.value)
    if not locations:
        flags.append(QualityFlag.OSM_INCOMPLETE.value)
    if not pop_values:
        flags.append(QualityFlag.POP_UNAVAILABLE.value)

    kpis: dict[str, Any] = {
        "flood_area_km2": flood_area,
        "buildings_in_water": b_in,
        "roads_in_water_km": round(sum(road_km_known), 3) if road_km_known else None,
        "hospitals_in_water": len(hospitals),
        "schools_in_water": len(schools),
        "pop_exposed_est": int(sum(pop_values)) if pop_values else None,
        "mean_confidence": confidence_mean,
    }
    if env_flag("FEATURE_ECONOMIC_LOSS", False):
        kpis["economic_loss_inr"] = None
        kpis["economic_loss_experimental"] = True

    existing = container.assessments.list_for_event(event_id)
    version = (existing[0].version + 1) if existing else 1
    assessment_id = ulid()
    for layer_name, feats in (
        ("buildings", buildings),
        ("roads", roads),
        ("amenities", amenities),
    ):
        uri = container.vectors.write_features(assessment_id, layer_name, feats)
        write_geoparquet_sidecar(Path(uri))
    zonal_features = [
        {
            "type": "Feature",
            "geometry": next(
                (
                    f.get("geometry")
                    for f in locations
                    if (f.get("properties") or {}).get("location_id") == z["location_id"]
                ),
                None,
            ),
            "properties": z,
        }
        for z in zonal
    ]
    zonal_uri = container.vectors.write_features(assessment_id, "zonal", zonal_features)
    write_geoparquet_sidecar(Path(zonal_uri))

    hosp_by_loc: dict[str, int] = {}
    for feat in hospitals:
        centroid = geometry_centroid(feat.get("geometry") or {})
        if centroid is None:
            continue
        loc = location_id_containing(centroid[0], centroid[1], locations)
        if loc:
            hosp_by_loc[loc] = hosp_by_loc.get(loc, 0) + 1

    weights = container.config.get("relief_weights") or {
        "pop": 0.4,
        "flood_frac": 0.4,
        "hospitals_hit": 0.2,
    }
    plan = build_relief_plan(assessment_id, zonal, hosp_by_loc, weights)
    container.vectors.write_features(
        assessment_id,
        "relief",
        [{"type": "Feature", "geometry": None, "properties": z} for z in plan.zones],
    )

    assessment = Assessment(
        assessment_id=assessment_id,
        event_id=event_id,
        version=version,
        job_id=job_id,
        disaster_type=event.disaster_type,
        model_cards=model_cards or {"flood": "s1-threshold-v0"},
        layers=[
            {
                "layer_id": ulid(),
                "name": name,
                "kind": "vector",
                "uri": f"/disaster/assessments/{assessment_id}/geojson?layer={name}",
                "media_type": "application/geo+json",
                "schema_version": "1.0",
            }
            for name in ("buildings", "roads", "amenities", "zonal")
        ],
        kpis=kpis,
        quality_flags=sorted(set(flags)),
        authenticity=authenticity,
        confidence_mean=confidence_mean,
        parent_assessment_id=existing[0].assessment_id if existing else None,
    )
    container.assessments.put(assessment)
    container.metrics["disaster_assessments_total"] = (
        int(container.metrics.get("disaster_assessments_total") or 0) + 1
    )
    for z in zonal:
        if z.get("location_id"):
            container.assessments.index_location(str(z["location_id"]), assessment_id)
    for loc_id in event.location_ids:
        container.assessments.index_location(loc_id, assessment_id)
    return assessment
