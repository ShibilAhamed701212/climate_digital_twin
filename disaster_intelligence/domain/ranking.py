from __future__ import annotations

from typing import Any


def _is_sar(item: dict[str, Any]) -> bool:
    blob = f"{item.get('collection') or ''} {(item.get('properties') or {}).get('platform') or ''}"
    lower = blob.lower()
    return "sentinel-1" in lower or "sar" in lower


def quality_score(item: dict[str, Any]) -> float:
    """0–1 catalog quality heuristic (not a scientific accuracy claim)."""
    score = 0.4
    if _is_sar(item):
        score += 0.35
    cloud = (item.get("properties") or {}).get("eo:cloud_cover")
    if cloud is not None:
        score += max(0.0, 0.25 * (1.0 - min(100.0, float(cloud)) / 100.0))
    else:
        score += 0.1
    return round(min(1.0, score), 3)


def rank_stac_features(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer Sentinel-1, then lower cloud cover, then newer acquisition (stable sorts)."""

    def cloud(item: dict[str, Any]) -> float:
        value = (item.get("properties") or {}).get("eo:cloud_cover")
        return float(value) if value is not None else 100.0

    def acquired(item: dict[str, Any]) -> str:
        return str((item.get("properties") or {}).get("datetime") or "")

    ranked = sorted(features, key=acquired, reverse=True)
    ranked = sorted(ranked, key=cloud)
    return sorted(ranked, key=lambda item: 0 if _is_sar(item) else 1)
