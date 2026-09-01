from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from disaster_intelligence import __version__
from disaster_intelligence.api.errors import from_disaster_error
from disaster_intelligence.api.metrics import prometheus_text
from disaster_intelligence.api.schemas import (
    DropIngestRequest,
    EventCreateRequest,
    JobCreateRequest,
    ReliefPlanRequest,
    StacIngestRequest,
)
from disaster_intelligence.application.container import get_container, reset_container
from disaster_intelligence.application.ingest import EventService, IngestService
from disaster_intelligence.application.integrations import public_integrations
from disaster_intelligence.application.janitor import apply_ttl
from disaster_intelligence.application.jobs import JobService, job_events
from disaster_intelligence.config import data_dir, env_flag
from disaster_intelligence.domain.errors import DisasterError, NotFoundError, ValidationError
from disaster_intelligence.domain.geometry import (
    envelope_intersects_bbox,
    geometry_envelope,
    simplify_geometry,
)
from disaster_intelligence.domain.paths import ALLOWED_LAYER_NAMES, safe_layer_name
from disaster_intelligence.domain.relief import build_relief_plan
from disaster_intelligence.domain.zonal import geometry_centroid, location_id_containing
from disaster_intelligence.inference.runtimes import selected_device, selected_runtime
from disaster_intelligence.models.registry import catalog
from disaster_intelligence.reports.render import (
    render_csv,
    render_geojson,
    render_json,
    render_markdown,
    render_pdf,
)

logger = logging.getLogger(__name__)
_REQUEST_ID: ContextVar[str] = ContextVar("die_request_id", default="")

os.environ.setdefault("GDAL_SKIP", "JPEG2000")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff,.cog")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_container()
    logger.info("Disaster Intelligence Engine %s started", __version__)
    yield
    reset_container()


app = FastAPI(
    title="Disaster Intelligence Engine",
    version=__version__,
    lifespan=lifespan,
)

_DIE_AUTH_EXEMPT = {"/health", "/health/live", "/metrics"}


class DieApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        key = os.environ.get("DIE_API_KEY", "")
        if not key:
            return await call_next(request)
        path = request.url.path.rstrip("/")
        if path in _DIE_AUTH_EXEMPT or path.startswith("/health"):
            return await call_next(request)
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ") if auth_header.startswith("Bearer ") else ""
        if not token or not secrets.compare_digest(token, key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key", "error_code": "UNAUTHORIZED"},
            )
        return await call_next(request)


class DieSecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class DieRequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        from disaster_intelligence.domain.ids import ulid

        rid = request.headers.get("X-Request-ID") or ulid()
        token = _REQUEST_ID.set(rid)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            _REQUEST_ID.reset(token)


class DieOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        allowed = os.environ.get("DIE_ALLOWED_ORIGINS", "").strip()
        if not allowed:
            return await call_next(request)
        origin = request.headers.get("Origin", "")
        hosts = {item.strip() for item in allowed.split(",") if item.strip()}
        if origin and origin not in hosts:
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin not allowed", "error_code": "FORBIDDEN"},
            )
        return await call_next(request)


app.add_middleware(DieApiKeyMiddleware)
app.add_middleware(DieSecurityHeadersMiddleware)
app.add_middleware(DieOriginMiddleware)
app.add_middleware(DieRequestIdMiddleware)


def _disk_writable() -> bool:
    try:
        probe = data_dir() / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _services() -> tuple[EventService, IngestService, JobService]:
    c = get_container()
    return EventService(c), IngestService(c), JobService(c)


@app.exception_handler(DisasterError)
async def disaster_error_handler(_request: Request, exc: DisasterError) -> JSONResponse:
    return from_disaster_error(exc)


@app.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health")
def health() -> dict[str, Any]:
    c = get_container()
    inflight = c.jobs.list_inflight()
    disk_ok = _disk_writable()
    c.metrics["disaster_disk_ok"] = 1 if disk_ok else 0
    return {
        "status": "healthy" if disk_ok else "degraded",
        "service": "disaster-engine",
        "version": __version__,
        "gpu": env_flag("GPU_ENABLED", False),
        "models": {
            "flood": os.environ.get("MODEL_FLOOD", "threshold"),
            "device": selected_device(),
            "runtime": selected_runtime(),
        },
        "job_running": bool(inflight),
        "disk_ok": disk_ok,
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(prometheus_text(), media_type="text/plain; version=0.0.4")


@app.post("/disaster/admin/ttl")
def run_ttl() -> dict[str, int]:
    return {"removed": apply_ttl()}


@app.post("/disaster/events", status_code=201)
def create_event(req: EventCreateRequest) -> dict[str, Any]:
    events, _, _ = _services()
    event = events.create_event(
        disaster_type=req.disaster_type,
        aoi=req.aoi,
        t_start=req.t_start,
        name=req.name,
        location_ids=req.location_ids,
        t_end=req.t_end,
    )
    return event.to_dict()


@app.get("/disaster/events")
def list_events(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    disaster_type: str | None = None,
) -> dict[str, Any]:
    events, _, _ = _services()
    items, total = events.list_events(limit, offset, disaster_type)
    return {"items": [e.to_dict() for e in items], "total": total, "limit": limit, "offset": offset}


@app.get("/disaster/events/{event_id}")
def get_event(event_id: str) -> dict[str, Any]:
    events, _, _ = _services()
    return events.get(event_id).to_dict()


@app.get("/disaster/events/{event_id}/assessments")
def list_event_assessments(
    event_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    c = get_container()
    items = c.assessments.list_for_event(event_id)
    total = len(items)
    sliced = items[offset : offset + limit]
    return {
        "items": [a.to_dict() for a in sliced],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.post("/disaster/ingest/stac")
def ingest_stac(req: StacIngestRequest) -> dict[str, Any]:
    _, ingest, _ = _services()
    return ingest.ingest_stac(req.event_id, req.collections, req.datetime, req.max_cloud_pct)


@app.post("/disaster/ingest/upload", status_code=201)
async def ingest_upload(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    event_id: str = Form(...),  # noqa: B008
    license: str = Form(...),  # noqa: B008
) -> dict[str, Any]:
    _, ingest, _ = _services()
    max_mb = int((get_container().config.get("limits") or {}).get("max_upload_mb") or 256)
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        overhead = 64 * 1024
        if int(content_length) > max_mb * 1024 * 1024 + overhead:
            raise ValidationError("Upload exceeds size limit", "PAYLOAD_TOO_LARGE")
    data = await file.read()
    scene = ingest.upload_scene(event_id, file.filename or "upload.tif", data, license)
    _audit("upload", scene.scene_id)
    return scene.to_dict()


@app.post("/disaster/ingest/drop", status_code=201)
def ingest_drop(req: DropIngestRequest) -> dict[str, Any]:
    _, ingest, _ = _services()
    result = ingest.ingest_drop(req.event_id, req.license)
    _audit("drop", req.event_id)
    return result


@app.post("/disaster/jobs", status_code=202)
def create_job(
    req: JobCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    _, _, jobs = _services()
    job = jobs.create_job(req.event_id, req.tasks, req.twin_sync, idempotency_key)
    return job.to_dict()


@app.get("/disaster/jobs")
def list_jobs(
    event_id: str | None = None,
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    items, total = get_container().jobs.list_jobs(event_id, limit, offset, status)
    return {"items": [j.to_dict() for j in items], "total": total, "limit": limit, "offset": offset}


@app.get("/disaster/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    _, _, jobs = _services()
    return jobs.get(job_id).to_dict()


@app.post("/disaster/jobs/{job_id}/cancel", status_code=202)
def cancel_job(job_id: str) -> dict[str, Any]:
    _, _, jobs = _services()
    return jobs.cancel(job_id).to_dict()


@app.get("/disaster/jobs/{job_id}/mask")
def get_job_mask(job_id: str) -> Response:
    _, _, jobs = _services()
    jobs.get(job_id)
    path = get_container().rasters.path_for(f"{job_id}_mask.tif")
    file = Path(path)
    if not file.exists():
        raise NotFoundError("mask not available")
    return Response(content=file.read_bytes(), media_type="image/tiff")


@app.get("/disaster/jobs/{job_id}/stream")
async def stream_job(job_id: str) -> StreamingResponse:
    _, _, jobs = _services()
    jobs.get(job_id)

    async def gen():
        seen = 0
        for _ in range(900):
            events = job_events(job_id)
            while seen < len(events):
                payload = events[seen]
                seen += 1
                yield f"data: {json.dumps(payload)}\n\n"
                if payload.get("stage") in {"done", "failed"}:
                    yield "event: done\ndata: {}\n\n"
                    return
            await asyncio.sleep(0.2)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/disaster/assessments/{assessment_id}")
def get_assessment(assessment_id: str) -> dict[str, Any]:
    assessment = get_container().assessments.get(assessment_id)
    if assessment is None:
        raise NotFoundError(f"Assessment {assessment_id} not found")
    return assessment.to_dict()


@app.get("/disaster/assessments/{assessment_id}/geojson")
def get_geojson(
    assessment_id: str,
    layer: str = "buildings",
    bbox: str | None = None,
    simplify: float = 0.0,
    limit: int = Query(2000, ge=1, le=5000),
    offset: int = Query(0, ge=0),
) -> JSONResponse:
    _ = simplify
    c = get_container()
    if c.assessments.get(assessment_id) is None:
        raise NotFoundError(f"Assessment {assessment_id} not found")
    features = c.vectors.read_features(assessment_id, safe_layer_name(layer))
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) == 4:
            minx, miny, maxx, maxy = parts

            def _in(feat: dict[str, Any]) -> bool:
                envelope = geometry_envelope(feat.get("geometry") or {})
                if envelope is None:
                    return False
                return envelope_intersects_bbox(envelope, minx, miny, maxx, maxy)

            features = [f for f in features if _in(f)]
    if simplify > 0:
        for feat in features:
            geom = feat.get("geometry")
            if isinstance(geom, dict):
                feat["geometry"] = simplify_geometry(geom, simplify)
    total = len(features)
    sliced = features[offset : offset + limit]
    return JSONResponse(
        {"type": "FeatureCollection", "features": sliced},
        headers={"X-Total-Count": str(total)},
    )


@app.get("/disaster/assessments/{assessment_id}/layers/{name}")
def get_layer(assessment_id: str, name: str) -> Response:
    c = get_container()
    assessment = c.assessments.get(assessment_id)
    if assessment is None:
        raise NotFoundError("assessment not found")
    if name not in ALLOWED_LAYER_NAMES:
        raise NotFoundError("layer not found")
    features = c.vectors.read_features(assessment_id, name)
    body = json.dumps({"type": "FeatureCollection", "features": features}).encode()
    return Response(
        content=body,
        media_type="application/geo+json",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(body)),
            "Content-Disposition": f'attachment; filename="{name}.geojson"',
        },
    )


@app.get("/disaster/twin/{location_id}")
def get_twin_overlay(location_id: str) -> dict[str, Any]:
    if not location_id or len(location_id) < 3:
        raise NotFoundError("invalid location_id")
    assessment = get_container().assessments.latest_for_location(location_id)
    if assessment is None:
        return {"location_id": location_id, "available": False}
    cards = assessment.model_cards or {}
    return {
        "location_id": location_id,
        "available": True,
        "assessment_id": assessment.assessment_id,
        "event_id": assessment.event_id,
        "disaster_type": assessment.disaster_type,
        "kpis": assessment.kpis,
        "quality_flags": assessment.quality_flags,
        "authenticity": assessment.authenticity,
        "model_cards": cards,
        "model_id": cards.get("flood"),
        "model_version": cards.get("version") or "0",
        "runtime": cards.get("runtime"),
        "device": cards.get("device"),
        "checkpoint_hash": cards.get("checkpoint_sha256"),
        "confidence_type": cards.get("confidence_type"),
        "fallback_status": cards.get("fallback"),
        "fallback_used": cards.get("fallback_used"),
        "fallback_reason": cards.get("fallback_reason"),
        "sensor": cards.get("sensor"),
        "polarization": cards.get("polarization"),
        "input_channels": cards.get("input_channels"),
        "processing_time": cards.get("processing_ms"),
        "confidence_mean": assessment.confidence_mean,
        "updated_at": assessment.created_at,
        "href_assessment": f"/disaster/assessments/{assessment.assessment_id}",
    }


@app.post("/disaster/relief/plan")
def relief_plan(req: ReliefPlanRequest) -> dict[str, Any]:
    c = get_container()
    assessment = c.assessments.get(req.assessment_id)
    if assessment is None:
        raise NotFoundError("assessment not found")
    zonal_feats = c.vectors.read_features(req.assessment_id, "zonal")
    zonal = [f.get("properties") or {} for f in zonal_feats]
    amenities = c.vectors.read_features(req.assessment_id, "amenities")
    hosp: dict[str, int] = {}
    for feat in amenities:
        props = feat.get("properties") or {}
        if props.get("amenity") == "hospital" and props.get("in_water"):
            centroid = geometry_centroid(feat.get("geometry") or {})
            if centroid is None:
                continue
            loc = location_id_containing(centroid[0], centroid[1], zonal_feats)
            if loc:
                hosp[loc] = hosp.get(loc, 0) + 1
    weights = c.config.get("relief_weights") or {}
    plan = build_relief_plan(req.assessment_id, zonal, hosp, weights)
    return plan.to_dict()


@app.get("/disaster/models")
def list_models() -> dict[str, Any]:
    return catalog()


@app.get("/disaster/integrations")
def list_integrations() -> dict[str, Any]:
    return public_integrations()


@app.get("/disaster/assessments/{assessment_id}/report")
def assessment_report(
    assessment_id: str,
    location: str = "unknown",
    fmt: str = Query("markdown", pattern="^(markdown|pdf|json|csv|geojson)$"),
) -> Response:
    assessment = get_container().assessments.get(assessment_id)
    if assessment is None:
        raise NotFoundError("assessment not found")
    if fmt == "json":
        return Response(content=render_json(location, assessment), media_type="application/json")
    if fmt == "csv":
        return Response(content=render_csv(assessment), media_type="text/csv")
    if fmt == "geojson":
        return JSONResponse(render_geojson(location, assessment))
    md = render_markdown(location, assessment)
    if fmt == "pdf":
        return Response(content=render_pdf(md), media_type="application/pdf")
    return PlainTextResponse(md, media_type="text/markdown")


def _audit(action: str, resource_id: str) -> None:
    line = json.dumps(
        {
            "action": action,
            "id": resource_id,
            "actor": "api_key",
            "request_id": _REQUEST_ID.get(),
        }
    )
    path = data_dir() / "jsonl" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
