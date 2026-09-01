"""Live CDSE Sentinel-1 VV/VH → U-Net → assessment verification.

Does not print credentials, tokens, or passwords.
Does not claim success unless rasters open and U-Net actually runs.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AOI = {
    "type": "Polygon",
    "coordinates": [[[76.00, 12.95], [76.15, 12.95], [76.15, 13.08], [76.00, 13.08], [76.00, 12.95]]],
}
DT_START = "2018-08-01T00:00:00Z"
DT_END = "2018-08-31T00:00:00Z"
LOCATION = "KA-HAS-001"


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _pick_item(items: list[dict]) -> dict:
    from disaster_intelligence.domain.s1_assets import select_s1_assets

    ranked: list[dict] = []
    for item in items:
        ident = str(item.get("id") or "")
        props = item.get("properties") or {}
        mode = str(props.get("sar:instrument_mode") or props.get("instrumentMode") or "IW")
        if "IW" not in mode.upper():
            continue
        if "GRD" not in ident.upper() and "grd" not in str(item.get("collection") or "").lower():
            continue
        try:
            plan = select_s1_assets(item)
        except Exception:
            continue
        if plan.get("mode") not in {"dual", "product"}:
            continue
        if plan.get("mode") == "dual" and plan["vv"] == plan["vh"]:
            continue
        ranked.append(item)
    if not ranked:
        raise RuntimeError("No dual-pol IW GRD item with separate VV and VH assets")
    return ranked[0]


def _summarize_item(item: dict) -> dict:
    from disaster_intelligence.domain.s1_assets import select_s1_assets

    props = item.get("properties") or {}
    assets = item.get("assets") or {}
    plan = select_s1_assets(item)
    vv_asset = assets.get("vv") or {}
    vh_asset = assets.get("vh") or {}
    return {
        "scene_id": item.get("id"),
        "datetime": props.get("datetime"),
        "platform": props.get("platform"),
        "instrument": props.get("instruments") or props.get("sar:instrument_mode"),
        "orbit": props.get("sat:orbit_state") or props.get("sat:absolute_orbit"),
        "polarizations": props.get("sar:polarizations"),
        "vv_href_host": (plan.get("vv") or "").split("/")[2] if plan.get("vv") else None,
        "vh_href_host": (plan.get("vh") or "").split("/")[2] if plan.get("vh") else None,
        "vv_checksum": vv_asset.get("checksum") or vv_asset.get("file:checksum"),
        "vh_checksum": vh_asset.get("checksum") or vh_asset.get("file:checksum"),
        "vv_equals_vh": (plan.get("vv") == plan.get("vh")) if plan.get("mode") == "dual" else False,
        "download_mode": plan.get("mode"),
    }


def _run_job(container, event_id: str, twin_sync: bool) -> dict:
    from disaster_intelligence.application.jobs import JobService
    from disaster_intelligence.domain.entities import Job

    job = Job.create(event_id, ["flood_extent", "osm_intersect", "zonal_stats"])
    container.jobs.create(job)
    started = time.perf_counter()
    JobService(container)._execute(job.job_id, twin_sync)
    elapsed = time.perf_counter() - started
    finished = container.jobs.get(job.job_id)
    assert finished is not None
    assessment = container.assessments.get(finished.assessment_id or "")
    kpis = assessment.kpis if assessment else {}
    cards = assessment.model_cards if assessment else {}
    water_px = 0
    mask_path = Path(container.rasters.path_for(f"{job.job_id}_mask.tif"))
    if mask_path.is_file():
        from disaster_intelligence.domain.geotiff import read_uint8_tiff

        rows, _w, _h = read_uint8_tiff(mask_path)
        water_px = sum(1 for row in rows for v in row if v > 0)
        total_px = sum(len(row) for row in rows)
    else:
        total_px = 0
    return {
        "job_id": job.job_id,
        "status": finished.status,
        "error": finished.error_message,
        "assessment_id": finished.assessment_id,
        "elapsed_s": round(elapsed, 3),
        "water_pixels": water_px,
        "total_pixels": total_px,
        "water_fraction": (water_px / total_px) if total_px else None,
        "kpis": kpis,
        "model_cards": cards,
        "quality_flags": assessment.quality_flags if assessment else [],
        "twin_sync_ok": finished.twin_sync_ok,
    }


def main() -> int:
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    _load_dotenv()
    report: dict = {"live_e2e": False, "blockers": []}

    from disaster_intelligence.adapters.stac.oauth import credential_status

    creds = bool(credential_status().get("cdse"))
    report["credentials_configured"] = creds
    print("credentials_configured=", creds)
    if not creds:
        print("CDSE credentials unavailable.")
        report["blockers"].append("CDSE credentials unavailable")
        Path("data/disaster/tmp/live_e2e_report.json").parent.mkdir(parents=True, exist_ok=True)
        Path("data/disaster/tmp/live_e2e_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return 2

    os.environ.setdefault("MODEL_DEVICE", "cpu")
    os.environ.setdefault("MODEL_BATCH_SIZE", "1")
    os.environ.setdefault("MODEL_TILE_SIZE", "512")
    os.environ["TWIN_POINTER_ENABLED"] = "true"
    twin_url = os.environ.get("TWIN_SERVICE_URL") or "http://127.0.0.1:8001"
    if "twin-state-mgr" in twin_url:
        twin_url = "http://127.0.0.1:8001"
    os.environ["TWIN_SERVICE_URL"] = twin_url
    ckpt_candidates = [
        Path(os.environ.get("MODEL_WEIGHTS_UNET") or ""),
        Path(r"D:/ClimateDigitalTwin/models/flood/unet/model.pt"),
        ROOT / "models" / "eo" / "flood" / "unet" / "model.pt",
    ]
    ckpt = next((p for p in ckpt_candidates if p.is_file()), None)
    if ckpt is None:
        print("U-Net checkpoint not found on disk")
        report["blockers"].append("U-Net checkpoint missing")
        Path("data/disaster/tmp/live_e2e_report.json").parent.mkdir(parents=True, exist_ok=True)
        Path("data/disaster/tmp/live_e2e_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return 3
    os.environ["MODEL_WEIGHTS_UNET"] = str(ckpt)
    print("unet_checkpoint_present=", True, "bytes=", ckpt.stat().st_size)
    live_dir = ROOT / "data" / "disaster" / "tmp" / "live_e2e"
    live_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DISASTER_DATA_DIR"] = str(live_dir)

    from disaster_intelligence.adapters.stac.cdse import CdseStacAdapter
    from disaster_intelligence.application.container import AppContainer, reset_container
    from disaster_intelligence.application.ingest import (
        EventService,
        IngestService,
        _bounds_from_aoi,
    )
    from disaster_intelligence.config import load_disaster_config, reset_disaster_config
    from disaster_intelligence.domain.s1_assets import select_s1_assets

    reset_disaster_config()
    reset_container()
    os.environ["MODEL_FLOOD"] = "unet"
    container = AppContainer()

    print("=== PHASE 2 CDSE search ===")

    stac_cfg = load_disaster_config().get("stac") or {}
    allow = list(stac_cfg.get("host_allowlist") or [])
    search_urls = [
        str(stac_cfg.get("search_url") or ""),
        "https://stac.dataspace.copernicus.eu/v1/search",
    ]
    items: list = []
    last_err: Exception | None = None
    for url in search_urls:
        if not url:
            continue
        try:
            adapter = CdseStacAdapter(
                search_url=url,
                cache_dir=live_dir / "stac_cache",
                host_allowlist=allow,
                cache_hours=6.0,
                timeout_s=90.0,
                collection_allowlist=["sentinel-1-grd"],
                max_pages=1,
                page_limit=10,
            )
            items = adapter.search(AOI, DT_START, DT_END, ["sentinel-1-grd"])
            if items:
                report["search_url_used_host"] = url.split("/")[2]
                break
        except Exception as exc:
            last_err = exc
            items = []
    if not items:
        print("CDSE search failed:", type(last_err).__name__ if last_err else "empty", last_err)
        report["blockers"].append(f"CDSE search: {last_err}")
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 3
    print("features", len(items))
    report["search_count"] = len(items)
    if not items:
        report["blockers"].append("CDSE search returned no features")
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 3

    try:
        item = _pick_item(items)
    except Exception as exc:
        report["blockers"].append(str(exc))
        print(exc)
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 3
    meta = _summarize_item(item)
    report["scene"] = meta
    print(json.dumps(meta, indent=2, default=str))
    if meta.get("vv_equals_vh"):
        report["blockers"].append("VV href equals VH href")
        return 4

    plan = select_s1_assets(item)
    event = EventService(container).create_event(
        disaster_type="flood",
        aoi=AOI,
        t_start=DT_START,
        name="live-cdse-s1-unet",
        location_ids=[LOCATION],
        t_end=DT_END,
    )
    ingest = IngestService(container)
    from disaster_intelligence.application.ingest import _scene_from_stac_item

    scene = _scene_from_stac_item(
        event.event_id, event.t_start, item, plan.get("vv") or plan.get("product")
    )
    container.scenes.upsert(scene)
    dest = container.rasters.path_for(f"{scene.scene_id}.tif")
    existing_zip = next((live_dir / "cogs").glob("*.zip"), None)
    if existing_zip is not None and existing_zip.stat().st_size > 0:
        dest = str(existing_zip.with_suffix(".tif"))
    print("=== PHASE 4 download VV/VH ===")
    try:
        ingest._download_scene_assets(
            scene,
            {
                "href": plan.get("product") or plan.get("vv"),
                "dest": dest,
                "plan": plan,
                "s1": True,
                "aoi_bounds": _bounds_from_aoi(AOI),
            },
        )
    except Exception as exc:
        print("Download/stack failed:", type(exc).__name__, exc)
        report["blockers"].append(f"download: {type(exc).__name__}: {exc}")
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 4

    vv_path = Path(str(dest).replace(".tif", "_vv.tif"))
    vh_path = Path(str(dest).replace(".tif", "_vh.tif"))
    meas = Path(str(dest)).with_suffix("") / "meas"
    if not vv_path.is_file():
        for name in ("vv.tiff", "vv.tif"):
            cand = meas / name
            if cand.is_file():
                vv_path = cand
                break
    if not vh_path.is_file():
        for name in ("vh.tiff", "vh.tif"):
            cand = meas / name
            if cand.is_file():
                vh_path = cand
                break
    zip_path = Path(str(dest)).with_suffix(".zip")
    stack_path = Path(str(dest).replace(".tif", "_stack.tif"))
    sizes = {
        "mode": plan.get("mode"),
        "vv_bytes": vv_path.stat().st_size if vv_path.is_file() else 0,
        "vh_bytes": vh_path.stat().st_size if vh_path.is_file() else 0,
        "product_bytes": zip_path.stat().st_size if zip_path.is_file() else (
            Path(dest).stat().st_size if Path(dest).is_file() else 0
        ),
        "stack_bytes": stack_path.stat().st_size if stack_path.is_file() else 0,
        "vv_sha256_sidecar": Path(str(vv_path) + ".sha256").read_text(encoding="utf-8").strip()
        if Path(str(vv_path) + ".sha256").is_file()
        else None,
        "vh_sha256_sidecar": Path(str(vh_path) + ".sha256").read_text(encoding="utf-8").strip()
        if Path(str(vh_path) + ".sha256").is_file()
        else None,
    }
    report["download"] = sizes
    print("download sizes", sizes["vv_bytes"], sizes["vh_bytes"])
    if sizes["vv_bytes"] <= 0 or sizes["vh_bytes"] <= 0:
        report["blockers"].append("downloaded rasters missing or empty")
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 4
    if sizes["vv_bytes"] == sizes["vh_bytes"]:
        import hashlib

        h1 = hashlib.sha256(vv_path.read_bytes()[:1024 * 1024]).hexdigest()
        h2 = hashlib.sha256(vh_path.read_bytes()[:1024 * 1024]).hexdigest()
        if h1 == h2:
            report["blockers"].append("VV and VH files share the same first-1MB hash")
            print("VV was duplicated into VH — aborting")
            return 4

    print("=== PHASE 5 raster validation ===")
    try:
        import rasterio

        with rasterio.open(vv_path) as src_vv, rasterio.open(vh_path) as src_vh:
            raster_info = {
                "vv_crs": str(src_vv.crs),
                "vh_crs": str(src_vh.crs),
                "vv_shape": [src_vv.height, src_vv.width],
                "vh_shape": [src_vh.height, src_vh.width],
                "same_crs": str(src_vv.crs) == str(src_vh.crs),
                "same_shape": src_vv.width == src_vh.width and src_vv.height == src_vh.height,
            }
            print(json.dumps(raster_info))
            report["rasters"] = raster_info
    except Exception as exc:
        report["blockers"].append(f"rasterio open failed: {exc}")
        print("Could not open downloaded rasters:", exc)
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 5

    from disaster_intelligence.preprocessing.sentinel1 import (
        load_s1_stack,
        standardize_vv_vh,
        tile_stack,
    )

    refreshed = container.scenes.get(scene.scene_id)
    stack = load_s1_stack(refreshed.local_uri if refreshed else "")
    if stack is None:
        report["blockers"].append("windowed VV/VH stack did not load")
        print("Stack missing after ingest")
        return 6
    print("stack", stack.height, stack.width, stack.bounds)
    report["preprocess"] = {
        "height": stack.height,
        "width": stack.width,
        "bounds": stack.bounds,
        "channel_0": "VV",
        "channel_1": "VH",
    }
    vv_z, vh_z = standardize_vv_vh(stack.vv, stack.vh)
    tiles = tile_stack(vv_z, vh_z, 512)
    if tiles:
        _y, _x, _h, _w, tv, th = tiles[0]
        report["preprocess"]["first_tile_vv_shape"] = [len(tv), len(tv[0]) if tv else 0]
        report["preprocess"]["tile_count"] = len(tiles)
        _ = th

    print("=== PHASE 7/8 U-Net ===")
    gpu = {"nvidia_smi": None, "torch_cuda": False}
    try:
        smi = subprocess.run(
            ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=20, check=False
        )
        gpu["nvidia_smi"] = (smi.stdout or smi.stderr or "")[:200]
    except Exception as exc:
        gpu["nvidia_smi"] = f"unavailable: {exc}"
    try:
        import torch

        gpu["torch_cuda"] = bool(torch.cuda.is_available())
    except Exception as exc:
        gpu["torch_cuda"] = False
        gpu["torch_import"] = str(exc)
    report["gpu"] = gpu
    print("cuda", gpu["torch_cuda"])
    if gpu["torch_cuda"] and os.environ.get("MODEL_DEVICE") != "cuda":
        print("CUDA is available in this process; this run stays on CPU as requested first.")

    print("=== PHASE 9-11 U-Net job + assessment + twin pointer ===")
    try:
        unet_job = _run_job(container, event.event_id, True)
    except Exception as exc:
        report["blockers"].append(f"unet job: {type(exc).__name__}: {exc}")
        print("U-Net job failed:", type(exc).__name__, exc)
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 7
    report["unet"] = unet_job
    print("unet status", unet_job["status"], "assessment", unet_job["assessment_id"])
    if unet_job["status"] != "completed":
        report["blockers"].append(f"unet job {unet_job['status']}: {unet_job['error']}")
        (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 7

    from disaster_intelligence.reports.render import (
        render_csv,
        render_geojson,
        render_json,
        render_markdown,
        render_pdf,
    )

    unet_assessment = container.assessments.get(str(unet_job["assessment_id"] or ""))
    if unet_assessment is not None:
        for loc in [LOCATION, *list(event.location_ids)]:
            container.assessments.index_location(loc, unet_assessment.assessment_id)
        cards = unet_assessment.model_cards or {}
        overlay = {
            "available": True,
            "location_id": LOCATION,
            "assessment_id": unet_assessment.assessment_id,
            "event_id": unet_assessment.event_id,
            "model_id": cards.get("flood"),
            "sensor": cards.get("sensor"),
            "polarization": cards.get("polarization"),
            "runtime": cards.get("runtime"),
            "device": cards.get("device"),
            "confidence_type": cards.get("confidence_type"),
            "checkpoint_hash": (cards.get("checkpoint_sha256") or "")[:16],
            "processing_time": cards.get("processing_ms"),
            "quality_flags": unet_assessment.quality_flags,
            "kpis": unet_assessment.kpis,
            "model_cards": cards,
            "href_assessment": f"/disaster/assessments/{unet_assessment.assessment_id}",
        }
        md = render_markdown(LOCATION, unet_assessment)
        reports = {
            "markdown": {"status": 200, "bytes": len(md.encode())},
            "json": {"status": 200, "bytes": len(render_json(LOCATION, unet_assessment))},
            "csv": {"status": 200, "bytes": len(render_csv(unet_assessment))},
            "geojson": {"status": 200, "bytes": len(str(render_geojson(LOCATION, unet_assessment)))},
            "pdf": {"status": 200, "bytes": len(render_pdf(md))},
        }
    else:
        overlay = {"available": False}
        reports = {}
    report["dashboard_overlay"] = overlay
    report["reports"] = reports
    report["copilot"] = {
        "source": f"/disaster/twin/{LOCATION}",
        "model_id": overlay.get("model_id"),
        "sensor": overlay.get("sensor"),
        "polarization": overlay.get("polarization"),
        "runtime": overlay.get("runtime"),
        "confidence_type": overlay.get("confidence_type"),
        "quality_flags": overlay.get("quality_flags"),
        "provenance": overlay.get("model_cards"),
        "processing_time": overlay.get("processing_time"),
        "assessment_id": overlay.get("assessment_id"),
    }
    print("overlay", json.dumps({k: overlay.get(k) for k in (
        "available", "assessment_id", "model_id", "sensor", "polarization",
        "runtime", "confidence_type", "checkpoint_hash",
    )}, default=str))
    report["unet"]["twin_sync_ok"] = unet_job.get("twin_sync_ok")

    print("=== PHASE 15 threshold comparison ===")
    os.environ["MODEL_FLOOD"] = "threshold"
    reset_disaster_config()
    reset_container()
    thresh_container = AppContainer()
    # Re-bind the same scene/event stores (same DISASTER_DATA_DIR).
    try:
        thresh_job = _run_job(thresh_container, event.event_id, False)
    except Exception as exc:
        report["blockers"].append(f"threshold job: {exc}")
        thresh_job = {"status": "failed", "error": str(exc)}
    report["threshold"] = thresh_job
    print("threshold status", thresh_job.get("status"), thresh_job.get("assessment_id"))

    print("=== PHASE 16 fallback (intentional: hide U-Net weights) ===")
    os.environ["MODEL_FLOOD"] = "unet"
    os.environ["MODEL_FLOOD_FALLBACK"] = "threshold"
    # Deliberate negative control: point at a missing checkpoint so fallback is explicit.
    os.environ["MODEL_WEIGHTS_UNET"] = str(live_dir / "missing-unet.pt")
    os.environ["MODEL_WEIGHTS_DIR"] = str(live_dir / "no-models")
    os.environ["MODEL_DIR"] = str(live_dir / "no-models")
    print("fallback_test_hides_weights=", True)
    reset_disaster_config()
    reset_container()
    fb_container = AppContainer()
    try:
        fb_job = _run_job(fb_container, event.event_id, False)
    except Exception as exc:
        report["blockers"].append(f"fallback job: {exc}")
        fb_job = {"status": "failed", "error": str(exc)}
    report["fallback"] = {
        "status": fb_job.get("status"),
        "assessment_id": fb_job.get("assessment_id"),
        "requested_model": (fb_job.get("model_cards") or {}).get("requested_model"),
        "actual_model": (fb_job.get("model_cards") or {}).get("actual_model"),
        "fallback_used": (fb_job.get("model_cards") or {}).get("fallback_used"),
        "fallback_reason": (fb_job.get("model_cards") or {}).get("fallback_reason"),
    }
    print("fallback", json.dumps(report["fallback"]))

    print("=== PHASE 17 health probes ===")
    import httpx

    probes = {}
    for name, url in [
        ("gateway", "http://127.0.0.1:8000/health"),
        ("die", "http://127.0.0.1:8008/health"),
        ("dashboard", "http://127.0.0.1:8501/healthz"),
        ("twin", "http://127.0.0.1:8001/health"),
        ("risk", "http://127.0.0.1:8003/health"),
        ("forecast", "http://127.0.0.1:8002/health"),
        ("copilot", "http://127.0.0.1:8005/health"),
        ("report", "http://127.0.0.1:8004/health"),
        ("rag", "http://127.0.0.1:8006/health"),
        ("ollama", "http://127.0.0.1:11434/api/tags"),
    ]:
        try:
            with httpx.Client(timeout=3.0) as http:
                resp = http.get(url)
            probes[name] = {"status": resp.status_code, "running": resp.status_code < 500}
        except Exception as exc:
            probes[name] = {"running": False, "error": type(exc).__name__}
    report["health_stack"] = probes
    report["health_die_inprocess"] = {
        "unet_job": unet_job.get("status"),
        "twin_sync_ok": unet_job.get("twin_sync_ok"),
    }

    print("=== PHASE 18 docker ===")
    docker = {}
    try:
        ps = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            cwd=str(ROOT),
        )
        docker["ps_exit"] = ps.returncode
        docker["ps_preview"] = (ps.stdout or ps.stderr or "")[:1500]
    except Exception as exc:
        docker["error"] = str(exc)
    report["docker"] = docker

    print("=== PHASE 20 cleanup .part ===")
    removed = []
    for part in live_dir.rglob("*.part"):
        part.unlink(missing_ok=True)
        removed.append(str(part.name))
    report["cleaned_part_files"] = removed

    unet_ok = (
        unet_job.get("status") == "completed"
        and (unet_job.get("model_cards") or {}).get("actual_model", "").startswith("unet")
        and (unet_job.get("model_cards") or {}).get("fallback_used") == "false"
        and sizes["vv_bytes"] > 0
        and sizes["vh_bytes"] > 0
        and overlay.get("available") is True
        and unet_job.get("twin_sync_ok") is True
    )
    report["live_e2e"] = bool(unet_ok)
    (live_dir / "live_e2e_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("live_e2e", report["live_e2e"])
    return 0 if unet_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
