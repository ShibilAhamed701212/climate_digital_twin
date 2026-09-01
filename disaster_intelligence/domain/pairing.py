from __future__ import annotations

from datetime import datetime

from disaster_intelligence.domain.entities import ImagePair, Scene
from disaster_intelligence.domain.ids import ulid


def parse_iso(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    return datetime.fromisoformat(text)


def scene_kind(scene: Scene) -> str:
    blob = " ".join(
        str(part).lower() for part in (scene.provider, scene.product, scene.platform) if part
    )
    if any(token in blob for token in ("nasadem", "worldpop", "srtm", "dem", "population")):
        return "aux"
    if "sentinel-2" in blob or "s2-l2a" in blob:
        return "optical"
    if "sentinel-1" in blob or "s1" in blob:
        return "sar"
    return "unknown"


def select_pair(
    event_id: str,
    scenes: list[Scene],
    t_start: str,
    min_days_before: int = 7,
) -> ImagePair:
    """Pick nearest post scene after t_start and optional pre scene >= min_days_before."""
    start = parse_iso(t_start)
    dated: list[tuple[datetime, Scene]] = []
    for scene in scenes:
        if scene_kind(scene) == "aux":
            continue
        try:
            dated.append((parse_iso(scene.acquired_at), scene))
        except ValueError:
            continue
    after_candidates = [(dt, s) for dt, s in dated if dt >= start]
    if not after_candidates:
        after_candidates = dated
    if not after_candidates:
        raise ValueError("No flood-mapping scenes available to pair")
    after_candidates.sort(key=lambda item: (_kind_rank(item[1]), item[0]))
    after = after_candidates[0][1]
    before: Scene | None = None
    pre = [(dt, s) for dt, s in dated if (start - dt).days >= min_days_before]
    if pre:
        pre.sort(key=lambda item: abs((start - item[0]).total_seconds()))
        before = pre[0][1]
    return ImagePair(
        pair_id=ulid(),
        event_id=event_id,
        after_scene_id=after.scene_id,
        before_scene_id=before.scene_id if before else None,
    )


def _kind_rank(scene: Scene) -> int:
    kind = scene_kind(scene)
    if kind == "sar":
        return 0
    if kind == "optical":
        return 1
    return 2
