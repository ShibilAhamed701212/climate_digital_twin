from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from disaster_intelligence.domain.errors import ValidationError
from disaster_intelligence.domain.geotiff import read_float32_vv_vh, write_float32_vv_vh
from disaster_intelligence.domain.s1_assets import (
    polarizations_from_stac,
    require_vv_vh,
    select_s1_assets,
)
from disaster_intelligence.preprocessing.sentinel1 import (
    CHANNEL_ORDER,
    extract_s1_measurements,
    load_s1_stack,
    standardize_vv_vh,
    stitch_mask,
    threshold_mask_from_vv,
    tile_stack,
    write_s1_sidecar,
)


def test_require_both_polarizations() -> None:
    require_vv_vh(["VV", "VH"])
    with pytest.raises(ValidationError) as exc:
        require_vv_vh(["VV"])
    assert exc.value.code == "INSUFFICIENT_POLARIZATION"


def test_cdse_s3_href_maps_to_https_object_store() -> None:
    from disaster_intelligence.adapters.stac.cdse import normalize_cdse_href

    href = normalize_cdse_href("s3://eodata/Sentinel-1/SAR/x.tif")
    assert href.startswith("https://eodata.dataspace.copernicus.eu/Sentinel-1/")
    assert "s3://" not in href


def test_select_dual_assets_not_product() -> None:
    item = {
        "id": "S1A_IW_GRDH_1SDV_x",
        "properties": {"sar:polarizations": ["VV", "VH"]},
        "assets": {
            "vv": {"href": "https://example.com/vv.tif"},
            "vh": {"href": "https://example.com/vh.tif"},
            "visual": {"href": "https://example.com/rgb.tif"},
        },
    }
    plan = select_s1_assets(item)
    assert plan["mode"] == "dual"
    assert plan["vv"].endswith("vv.tif")
    assert plan["vh"].endswith("vh.tif")


def test_missing_vh_not_duplicated() -> None:
    item = {
        "id": "S1A_IW_GRDH_1SSV_x",
        "properties": {"sar:polarizations": ["VV"]},
        "assets": {"vv": {"href": "https://example.com/vv.tif"}},
    }
    with pytest.raises(ValidationError) as exc:
        select_s1_assets(item)
    assert exc.value.code == "INSUFFICIENT_POLARIZATION"


def test_product_zip_when_no_separate_bands() -> None:
    item = {
        "id": "S1A_IW_GRDH_1SDV_x",
        "properties": {"sar:polarizations": ["VV", "VH"]},
        "assets": {"PRODUCT": {"href": "https://download.dataspace.copernicus.eu/x.zip"}},
    }
    plan = select_s1_assets(item)
    assert plan["mode"] == "product"


def test_https_product_preferred_over_s3_band_hrefs() -> None:
    item = {
        "id": "S1A_IW_GRDH_1SDV_x",
        "properties": {"sar:polarizations": ["VV", "VH"]},
        "assets": {
            "vv": {"href": "s3://eodata/vv.tif"},
            "vh": {"href": "s3://eodata/vh.tif"},
            "Product": {"href": "https://download.dataspace.copernicus.eu/x.zip"},
        },
    }
    plan = select_s1_assets(item)
    assert plan["mode"] == "product"
    assert plan["product"].startswith("https://")


def test_stac_dv_name_implies_vv_vh() -> None:
    pols = polarizations_from_stac({"id": "S1A_IW_GRDH_1SDV_abc", "properties": {}})
    assert "VV" in pols and "VH" in pols


def test_float_stack_roundtrip_and_geo(tmp_path: Path) -> None:
    vv = [[-12.0, -16.0], [-9.0, -20.0]]
    vh = [[-18.0, -22.0], [-17.0, -25.0]]
    path = tmp_path / "stack.tif"
    write_float32_vv_vh(path, vv, vh, west=76.0, north=13.0, xres=0.01, yres=0.01)
    got_vv, got_vh, geo = read_float32_vv_vh(path)
    assert got_vv[0][1] == pytest.approx(-16.0)
    assert got_vh[1][1] == pytest.approx(-25.0)
    assert geo["west"] == pytest.approx(76.0)
    assert geo["north"] == pytest.approx(13.0)
    sidecar = tmp_path / "x.s1.json"
    write_s1_sidecar(sidecar, path, {"west": 76.0, "east": 76.02, "south": 12.98, "north": 13.0})
    stack = load_s1_stack(str(sidecar))
    assert stack is not None
    assert stack.polarizations == CHANNEL_ORDER
    assert stack.vv[0][0] == pytest.approx(-12.0)


def test_standardize_and_tiles() -> None:
    vv = [[-10.85569763176121] * 8 for _ in range(8)]
    vh = [[-18.10330009462964] * 8 for _ in range(8)]
    zvv, zvh = standardize_vv_vh(vv, vh)
    assert zvv[0][0] == pytest.approx(0.0, abs=1e-5)
    assert zvh[0][0] == pytest.approx(0.0, abs=1e-5)
    tiles = tile_stack(vv, vh, tile=5)
    assert len(tiles) == 4
    parts = [(y, x, ph, pw, [[1] * pw for _ in range(ph)]) for y, x, ph, pw, _a, _b in tiles]
    mask = stitch_mask(8, 8, parts)
    assert mask[7][7] == 1


def test_channel_order_vv_then_vh(tmp_path: Path) -> None:
    vv = [[1.0, 2.0]]
    vh = [[3.0, 4.0]]
    path = tmp_path / "s.tif"
    write_float32_vv_vh(path, vv, vh)
    a, b, _geo = read_float32_vv_vh(path)
    assert a[0] == [pytest.approx(1.0), pytest.approx(2.0)]
    assert b[0] == [pytest.approx(3.0), pytest.approx(4.0)]


def test_zip_extract_vv_vh(tmp_path: Path) -> None:
    vv = [[-11.0]]
    vh = [[-19.0]]
    vv_tif = tmp_path / "s1a-iw-grd-vv-x.tiff"
    vh_tif = tmp_path / "s1a-iw-grd-vh-x.tiff"
    write_float32_vv_vh(vv_tif, vv, [[0.0]])
    write_float32_vv_vh(vh_tif, [[0.0]], vh)
    zpath = tmp_path / "prod.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.write(vv_tif, "measurement/s1a-iw-grd-vv-x.tiff")
        zf.write(vh_tif, "measurement/s1a-iw-grd-vh-x.tiff")
    got_vv, got_vh = extract_s1_measurements(zpath, tmp_path / "out")
    assert got_vv.name.startswith("vv")
    assert got_vh.name.startswith("vh")
    stack = load_s1_stack(str(zpath))
    assert stack is not None
    assert stack.vv[0][0] == pytest.approx(-11.0)
    assert stack.vh[0][0] == pytest.approx(-19.0)


def test_threshold_vv_db() -> None:
    mask = threshold_mask_from_vv([[-10.0, -20.0]], -16.0)
    assert mask == [[0, 1]]


def test_job_threshold_on_vvvh_stack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from disaster_intelligence.api.main import app
    from disaster_intelligence.application.container import get_container, reset_container
    from disaster_intelligence.application.jobs import JobService
    from disaster_intelligence.config import reset_disaster_config
    from disaster_intelligence.domain.entities import Job

    monkeypatch.setenv("DISASTER_DATA_DIR", str(tmp_path / "disaster"))
    monkeypatch.setenv("TWIN_POINTER_ENABLED", "false")
    monkeypatch.setenv("MODEL_FLOOD", "threshold")
    reset_disaster_config()
    reset_container()
    client = TestClient(app)
    aoi = {
        "type": "Polygon",
        "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
    }
    created = client.post(
        "/disaster/events",
        json={
            "disaster_type": "flood",
            "aoi": aoi,
            "t_start": "2018-08-15T00:00:00Z",
            "location_ids": ["KA-HAS-001"],
        },
    )
    assert created.status_code == 201
    event_id = created.json()["event_id"]
    c = get_container()
    stack_path = Path(c.rasters.path_for("stack.tif"))
    write_float32_vv_vh(
        stack_path,
        [[-10.0, -20.0], [-10.0, -20.0]],
        [[-18.0, -22.0], [-18.0, -22.0]],
        west=75.8,
        north=13.2,
        xres=0.3,
        yres=0.2,
    )
    sidecar = Path(c.rasters.path_for("stack.s1.json"))
    write_s1_sidecar(
        sidecar,
        stack_path,
        {"west": 75.8, "east": 76.4, "south": 12.8, "north": 13.2},
    )
    from disaster_intelligence.domain.entities import Scene

    scene = Scene(
        scene_id="s1vvvh",
        provider="sentinel-1",
        acquired_at="2018-08-16T00:00:00Z",
        license="test",
        authenticity="USER_UPLOAD",
        event_id=event_id,
        product="grd",
        local_uri=str(sidecar),
        bounds={"west": 75.8, "east": 76.4, "south": 12.8, "north": 13.2},
    )
    c.scenes.upsert(scene)
    job = Job.create(event_id, ["flood_extent", "osm_intersect", "zonal_stats"])
    c.jobs.create(job)
    JobService(c)._execute(job.job_id, False)
    finished = c.jobs.get(job.job_id)
    assert finished is not None and finished.status == "completed"
    assessment = c.assessments.get(finished.assessment_id or "")
    assert assessment is not None
    assert assessment.model_cards.get("polarization") == "VV+VH"
    assert "s1_vv_vh" in assessment.quality_flags
    reset_container()
    reset_disaster_config()


def test_window_vv_vh_does_not_duplicate_channels(tmp_path: Path) -> None:
    rasterio = pytest.importorskip("rasterio")
    np = pytest.importorskip("numpy")
    from rasterio.transform import from_origin

    vv_path = tmp_path / "vv.tif"
    vh_path = tmp_path / "vh.tif"
    transform = from_origin(76.0, 13.1, 0.01, 0.01)
    profile = {
        "driver": "GTiff",
        "height": 20,
        "width": 20,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": transform,
    }
    with rasterio.open(vv_path, "w", **profile) as dst:
        dst.write(np.full((20, 20), -12.0, dtype="float32"), 1)
    with rasterio.open(vh_path, "w", **profile) as dst:
        dst.write(np.full((20, 20), -19.0, dtype="float32"), 1)
    from disaster_intelligence.preprocessing.sentinel1 import window_vv_vh_to_aoi

    stack = window_vv_vh_to_aoi(
        vv_path,
        vh_path,
        {"west": 76.0, "south": 12.9, "east": 76.15, "north": 13.1},
        max_side=16,
    )
    assert min(stack.height, stack.width) >= 8
    assert stack.vv != stack.vh
    assert stack.vv[0][0] == pytest.approx(-12.0)
    assert stack.vh[0][0] == pytest.approx(-19.0)


def test_window_vv_vh_warps_gcp_only_rasters(tmp_path: Path) -> None:
    rasterio = pytest.importorskip("rasterio")
    np = pytest.importorskip("numpy")
    from rasterio.control import GroundControlPoint

    vv_path = tmp_path / "vv.tif"
    vh_path = tmp_path / "vh.tif"
    profile = {
        "driver": "GTiff",
        "height": 20,
        "width": 20,
        "count": 1,
        "dtype": "float32",
    }
    gcps = [
        GroundControlPoint(row=0, col=0, x=76.0, y=13.1),
        GroundControlPoint(row=0, col=19, x=76.19, y=13.1),
        GroundControlPoint(row=19, col=0, x=76.0, y=12.91),
        GroundControlPoint(row=19, col=19, x=76.19, y=12.91),
    ]
    with rasterio.open(vv_path, "w", **profile) as dst:
        dst.write(np.full((20, 20), -11.0, dtype="float32"), 1)
        dst.gcps = (gcps, "EPSG:4326")
    with rasterio.open(vh_path, "w", **profile) as dst:
        dst.write(np.full((20, 20), -20.0, dtype="float32"), 1)
        dst.gcps = (gcps, "EPSG:4326")
    from disaster_intelligence.preprocessing.sentinel1 import window_vv_vh_to_aoi

    stack = window_vv_vh_to_aoi(
        vv_path,
        vh_path,
        {"west": 76.0, "south": 12.91, "east": 76.19, "north": 13.1},
        max_side=16,
    )
    assert min(stack.height, stack.width) >= 8
    assert stack.vv != stack.vh
    assert stack.bounds["west"] < stack.bounds["east"]
