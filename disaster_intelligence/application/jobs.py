from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from disaster_intelligence.application.assessment import run_assessment
from disaster_intelligence.application.container import AppContainer
from disaster_intelligence.application.ingest import _bounds_from_aoi
from disaster_intelligence.application.preprocess import (
    clip_to_aoi,
    cloud_mask_flags,
    load_scene_rows,
    quality_control,
    sar_preprocess,
    write_tiles,
)
from disaster_intelligence.config import env_str
from disaster_intelligence.domain.entities import Job, TwinOverlayPointer, utc_iso
from disaster_intelligence.domain.enums import JobStatus, QualityFlag
from disaster_intelligence.domain.errors import ConflictError, NotFoundError, ValidationError
from disaster_intelligence.domain.geotiff import write_uint8_tiff
from disaster_intelligence.domain.pairing import scene_kind, select_pair
from disaster_intelligence.domain.policies import validate_tasks
from disaster_intelligence.inference.unet import UNetFloodRunner
from disaster_intelligence.preprocessing.sentinel1 import load_s1_stack, threshold_mask_from_vv

logger = logging.getLogger(__name__)

_RUN_LOCK = threading.Lock()
_LISTENERS: dict[str, list[dict[str, Any]]] = {}
_CANCEL: dict[str, threading.Event] = {}


def _emit(job_id: str, stage: str, pct: int, message: str) -> None:
    events = _LISTENERS.setdefault(job_id, [])
    events.append({"stage": stage, "pct": pct, "message": message})
    if len(events) > 200:
        del events[:-200]
    while len(_LISTENERS) > 64:
        oldest = next((k for k in _LISTENERS if k != job_id), None)
        if oldest is None:
            break
        _LISTENERS.pop(oldest, None)


def job_events(job_id: str) -> list[dict[str, Any]]:
    return list(_LISTENERS.get(job_id) or [])


class JobService:
    def __init__(self, container: AppContainer) -> None:
        self._c = container

    def create_job(
        self,
        event_id: str,
        tasks: list[str] | None,
        twin_sync: bool,
        idempotency_key: str | None,
    ) -> Job:
        if idempotency_key:
            existing = self._c.jobs.get_by_idempotency(idempotency_key)
            if existing:
                return existing
        event = self._c.events.get(event_id)
        if event is None:
            raise NotFoundError(f"Event {event_id} not found")
        if self._c.jobs.list_inflight():
            raise ConflictError("A disaster job is already running", "JOB_BUSY")
        job = Job.create(event_id, validate_tasks(tasks or []), idempotency_key)
        self._c.jobs.create(job)
        self._c.bump_job_metric("queued")
        _CANCEL[job.job_id] = threading.Event()
        thread = threading.Thread(
            target=self._run,
            args=(job.job_id, twin_sync),
            daemon=True,
            name=f"die-job-{job.job_id}",
        )
        thread.start()
        return job

    def get(self, job_id: str) -> Job:
        job = self._c.jobs.get(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found")
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        if job.status in {
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        }:
            raise ConflictError("Job already terminal")
        _CANCEL.setdefault(job_id, threading.Event()).set()
        job.status = JobStatus.CANCELLED.value
        job.finished_at = utc_iso()
        job.stage = "cancelled"
        updated = self._c.jobs.update(job)
        _emit(job_id, "cancelled", job.progress_pct, "Job cancelled")
        return updated

    def _abort_if_cancelled(self, job_id: str) -> None:
        flag = _CANCEL.get(job_id)
        if flag is not None and flag.is_set():
            raise ConflictError("Job cancelled")
        current = self.get(job_id)
        if current.status == JobStatus.CANCELLED.value:
            raise ConflictError("Job cancelled")

    def _run(self, job_id: str, twin_sync: bool) -> None:
        if not _RUN_LOCK.acquire(blocking=False):
            job = self._c.jobs.get(job_id)
            if job:
                job.status = JobStatus.FAILED.value
                job.error_code = "JOB_BUSY"
                job.error_message = "Another job holds the single-flight lock"
                self._c.jobs.update(job)
            return
        try:
            self._execute(job_id, twin_sync)
        finally:
            _RUN_LOCK.release()
            self._c.metrics["disaster_inflight_jobs"] = 0

    def _execute(self, job_id: str, twin_sync: bool) -> None:
        job = self.get(job_id)
        job.status = JobStatus.RUNNING.value
        job.started_at = utc_iso()
        job.stage = "preprocess"
        job.progress_pct = 10
        self._c.jobs.update(job)
        self._c.metrics["disaster_inflight_jobs"] = 1
        _emit(job_id, "preprocess", 10, "Loading scenes")
        try:
            event = self._c.events.get(job.event_id)
            if event is None:
                raise NotFoundError("event missing")
            self._abort_if_cancelled(job_id)
            scenes = self._c.scenes.list_for_event(job.event_id)
            if not scenes:
                raise ValidationError("No scenes ingested for event")
            pair = select_pair(
                job.event_id,
                scenes,
                event.t_start,
                int((self._c.config.get("pairing") or {}).get("min_days_before") or 7),
            )
            after = self._c.scenes.get(pair.after_scene_id)
            if after is None or not after.local_uri:
                raise ValidationError("After scene has no local raster (upload or download first)")
            if scene_kind(after) == "aux":
                raise ValidationError(
                    "Auxiliary rasters (DEM/population) cannot be used for flood extent",
                    "INVALID_GEOTIFF",
                )
            stack = load_s1_stack(after.local_uri)
            requested = env_str("MODEL_FLOOD", "threshold").strip().lower()
            max_pixels = int((self._c.config.get("limits") or {}).get("max_pixels") or 16_000_000)
            flags: list[str] = []
            rows: list[list[int]] = []
            if stack is not None:
                if stack.width * stack.height > max_pixels:
                    raise ValidationError("Raster exceeds max_pixels", "PAYLOAD_TOO_LARGE")
                flags.append(QualityFlag.S1_VV_VH.value)
                if min(stack.width, stack.height) < 8:
                    flags.append("low_res")
            else:
                loaded = load_scene_rows(after.local_uri)
                rows = clip_to_aoi(loaded) if scene_kind(after) == "optical" else sar_preprocess(loaded)
                flags.extend(quality_control(rows, max_pixels))
            flags.extend(cloud_mask_flags(after.provider, after.product or ""))
            if pair.before_scene_id is None:
                flags.append(QualityFlag.S1_ONLY.value)
            self._abort_if_cancelled(job_id)
            if rows:
                write_tiles(Path(after.local_uri).parent / f"tiles_{job.job_id}", rows)
            job.stage = "infer"
            job.progress_pct = 40
            self._c.jobs.update(job)
            _emit(job_id, "infer", 40, "Flood segmentation")
            self._abort_if_cancelled(job_id)
            runner = self._c.flood_runner
            bounds = after.bounds or _bounds_from_aoi(event.aoi)
            if isinstance(runner, UNetFloodRunner) and stack is not None:
                mask = runner.mask_from_vv_vh(stack.vv, stack.vh)
                confidence = runner.boundary_confidence(rows)
                bounds = stack.bounds or bounds
            elif isinstance(runner, UNetFloodRunner) and stack is None:
                mask = runner.mask_from_rows(rows)
                confidence = runner.boundary_confidence(rows)
            elif stack is not None and requested in {"threshold", "s1-threshold-v0", "s1-threshold"}:
                vv_db = float((self._c.config.get("flood_threshold") or {}).get("vv_db") or -16.0)
                mask = threshold_mask_from_vv(stack.vv, vv_db)
                confidence = runner.boundary_confidence(rows) if rows else None
                bounds = stack.bounds or bounds
            else:
                mask = runner.mask_from_rows(rows)
                confidence = runner.boundary_confidence(rows)
            extra_flags = list(getattr(runner, "last_flags", []) or [])
            if getattr(runner, "fallback_used", False):
                extra_flags.append(QualityFlag.THRESHOLD_FALLBACK.value)
            flags.extend(extra_flags)
            write_uint8_tiff(
                Path(self._c.rasters.path_for(f"{job.job_id}_mask.tif")),
                mask,
                width=len(mask[0]) if mask else 0,
                height=len(mask),
            )
            job.stage = "assess"
            job.progress_pct = 70
            self._c.jobs.update(job)
            _emit(job_id, "assess", 70, "Intersecting OSM and zonal stats")
            provenance = (
                runner.provenance()
                if hasattr(runner, "provenance")
                else {"flood": "s1-threshold-v0"}
            )
            if stack is not None:
                provenance["sensor"] = "sentinel-1"
                provenance["polarization"] = "VV+VH"
                provenance["input_channels"] = "2"
            assessment = run_assessment(
                self._c,
                event_id=job.event_id,
                job_id=job.job_id,
                mask=mask,
                bounds=bounds,
                authenticity=after.authenticity,
                quality_flags=flags,
                confidence_mean=confidence,
                model_cards=provenance,
            )
            twin_ok = None
            if twin_sync:
                job.stage = "pointer"
                job.progress_pct = 90
                self._c.jobs.update(job)
                twin_ok = True
                try:
                    location_ids = list(event.location_ids)
                    zonal = self._c.vectors.read_features(assessment.assessment_id, "zonal")
                    for feat in zonal:
                        loc = str((feat.get("properties") or {}).get("location_id") or "")
                        if loc:
                            location_ids.append(loc)
                    for loc in sorted(set(location_ids)):
                        pointer = TwinOverlayPointer(
                            location_id=loc,
                            assessment_id=assessment.assessment_id,
                            event_id=event.event_id,
                            disaster_type=event.disaster_type,
                            href_assessment=f"/disaster/assessments/{assessment.assessment_id}",
                            updated_at=utc_iso(),
                            kpis=assessment.kpis,
                        )
                        self._c.twin_pointer.upsert(pointer)
                except Exception as exc:
                    logger.warning("Twin pointer failed: %s", exc)
                    twin_ok = False
                assessment.twin_sync_ok = twin_ok
                self._c.assessments.put(assessment)
            self._abort_if_cancelled(job_id)
            job.status = JobStatus.COMPLETED.value
            job.assessment_id = assessment.assessment_id
            job.twin_sync_ok = twin_ok
            job.progress_pct = 100
            job.stage = "done"
            job.finished_at = utc_iso()
            self._c.jobs.update(job)
            self._c.bump_job_metric("completed")
            _emit(job_id, "done", 100, "Assessment complete")
        except Exception as exc:
            current = self._c.jobs.get(job_id)
            if current is not None and current.status == JobStatus.CANCELLED.value:
                _emit(job_id, "cancelled", current.progress_pct, "Job cancelled")
                return
            logger.exception("Disaster job failed")
            job.status = JobStatus.FAILED.value
            job.error_code = getattr(exc, "code", "JOB_FAILED")
            job.error_message = str(exc)
            job.finished_at = utc_iso()
            job.stage = "failed"
            self._c.jobs.update(job)
            self._c.bump_job_metric("failed")
            _emit(job_id, "failed", job.progress_pct, job.error_message or "failed")
