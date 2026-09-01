from __future__ import annotations

from enum import StrEnum


class DisasterType(StrEnum):
    FLOOD = "flood"
    CYCLONE = "cyclone"
    EARTHQUAKE = "earthquake"
    LANDSLIDE = "landslide"
    WILDFIRE = "wildfire"
    HEATWAVE = "heatwave"
    DROUGHT = "drought"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Authenticity(StrEnum):
    REAL = "REAL"
    SYNTHETIC = "SYNTHETIC"
    USER_UPLOAD = "USER_UPLOAD"


class QualityFlag(StrEnum):
    OK = "ok"
    CLOUD_CONTAMINATED = "cloud_contaminated"
    MISALIGNED = "misaligned"
    LOW_RES = "low_res"
    S1_ONLY = "s1_only"
    OPTICAL_CLOUD_UNMASKED = "optical_cloud_unmasked"
    AUX_RASTER_EXCLUDED = "aux_raster_excluded"
    POP_UNAVAILABLE = "pop_unavailable"
    OSM_INCOMPLETE = "osm_incomplete"
    INUNDATION_PROXY_NOT_STRUCTURAL = "inundation_proxy_not_structural"
    THRESHOLD_FALLBACK = "threshold_fallback"
    LEARNED_INPUT_INCOMPATIBLE = "learned_input_incompatible"
    S1_VV_VH = "s1_vv_vh"
    INSUFFICIENT_POLARIZATION = "insufficient_polarization"


class DamageClass(StrEnum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"
    DESTROYED = "destroyed"
    UNKNOWN = "unknown"


class LayerKind(StrEnum):
    RASTER = "raster"
    VECTOR = "vector"


MVP_TASKS = ("flood_extent", "osm_intersect", "zonal_stats", "relief_v0")
ENABLED_DISASTER_TYPES = (DisasterType.FLOOD,)
