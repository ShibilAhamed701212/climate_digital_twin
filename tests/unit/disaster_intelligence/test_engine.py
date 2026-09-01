from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from disaster_intelligence.application.container import reset_container
from disaster_intelligence.config import reset_disaster_config
from disaster_intelligence.domain.entities import Scene
from disaster_intelligence.domain.errors import ValidationError
from disaster_intelligence.domain.geotiff import write_uint8_tiff
from disaster_intelligence.domain.ids import ulid
from disaster_intelligence.domain.intersect import intersect_osm
from disaster_intelligence.domain.pairing import select_pair
from disaster_intelligence.domain.policies import aoi_within_bounds, validate_tasks
from disaster_intelligence.domain.relief import score_zones
from disaster_intelligence.domain.zonal import flood_fraction_for_polygon, zonal_stats


@pytest.fixture
def isolated_die(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DISASTER_DATA_DIR", str(tmp_path / "disaster"))
    monkeypatch.setenv("TWIN_POINTER_ENABLED", "false")
    for key in (
        "CDSE_USERNAME",
        "CDSE_PASSWORD",
        "EARTHDATA_USERNAME",
        "EARTHDATA_PASSWORD",
        "EARTHDATA_TOKEN",
        "SH_CLIENT_ID",
        "SH_CLIENT_SECRET",
        "DIE_API_KEY",
        "MODEL_WEIGHTS_DIR",
        "MODEL_WEIGHTS_UNET",
        "GPU_ENABLED",
        "MODEL_DEVICE",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("MODEL_DEVICE", "cpu")
    reset_disaster_config()
    reset_container()
    yield tmp_path
    reset_container()
    reset_disaster_config()


class TestDomain:
    def test_ulid_length(self) -> None:
        assert len(ulid()) == 26

    def test_validate_tasks_default(self) -> None:
        assert "flood_extent" in validate_tasks([])

    def test_aoi_outside(self) -> None:
        aoi = {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
        }
        with pytest.raises(ValidationError):
            aoi_within_bounds(
                aoi, {"min_lat": 11.5, "max_lat": 18.5, "min_lon": 74.0, "max_lon": 78.5}, False
            )

    def test_pairing_s1_only(self) -> None:
        scenes = [
            Scene(
                scene_id="a",
                provider="sentinel-1",
                acquired_at="2018-08-16T00:00:00Z",
                license="copernicus-open",
                authenticity="REAL",
            )
        ]
        pair = select_pair("e1", scenes, "2018-08-15T00:00:00Z")
        assert pair.after_scene_id == "a"
        assert pair.before_scene_id is None

    def test_zonal_and_intersect(self) -> None:
        mask = [[1, 1], [0, 0]]
        bounds = {"west": 76.0, "east": 76.02, "south": 12.89, "north": 12.92}
        ring = [[76.0, 12.9], [76.01, 12.9], [76.01, 12.91], [76.0, 12.91], [76.0, 12.9]]
        frac = flood_fraction_for_polygon(ring, mask, bounds)
        assert 0.0 <= frac <= 1.0
        feats = [
            {
                "type": "Feature",
                "properties": {"osm_id": 1, "building": "yes"},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ]
        out = intersect_osm(feats, mask, bounds)
        assert "in_water" in out[0]["properties"]
        locs = [
            {
                "type": "Feature",
                "properties": {"location_id": "KA-HAS-001", "population": 1000},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ]
        rows = zonal_stats(locs, mask, bounds, 0.01)
        assert rows[0]["location_id"] == "KA-HAS-001"

    def test_relief_ranks(self) -> None:
        zones = score_zones(
            [{"location_id": "A", "flood_fraction": 0.9, "pop_exposed_est": 50000}],
            {"A": 2},
            {"pop": 0.4, "flood_frac": 0.4, "hospitals_hit": 0.2},
        )
        assert zones[0]["rank"] == 1

    def test_geotiff_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "m.tif"
        write_uint8_tiff(path, [[10, 200], [10, 200]], width=2, height=2)
        from disaster_intelligence.domain.geotiff import read_uint8_tiff, sniff_tiff_magic

        assert sniff_tiff_magic(path.read_bytes())
        rows, w, h = read_uint8_tiff(path)
        assert (w, h) == (2, 2)
        assert rows[0][0] == 10


class TestDieApi:
    def test_health_and_models(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        live = client.get("/health/live")
        assert live.status_code == 200
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["service"] == "disaster-engine"
        models = client.get("/disaster/models")
        assert models.status_code == 200
        ids = {item["id"] for item in models.json()["items"]}
        assert "s1-threshold-v0" in ids
        assert "unet" in ids
        integ = client.get("/disaster/integrations")
        assert integ.status_code == 200
        assert integ.json()["credentials_configured"]["cdse"] is False
        assert live.headers.get("X-Request-ID")
        models_body = models.json()
        assert models_body["device"] == "cpu"

    def test_event_upload_job_overlay(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app
        from disaster_intelligence.application.container import get_container
        from disaster_intelligence.application.jobs import JobService
        from disaster_intelligence.domain.entities import Job

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
                "name": "test",
            },
        )
        assert created.status_code == 201
        event_id = created.json()["event_id"]
        tif = isolated_die / "up.tif"
        write_uint8_tiff(
            tif,
            [[10] * 8 for _ in range(8)],
            width=8,
            height=8,
        )
        upload = client.post(
            "/disaster/ingest/upload",
            files={"file": ("up.tif", tif.read_bytes(), "image/tiff")},
            data={"event_id": event_id, "license": "test"},
        )
        assert upload.status_code == 201
        container = get_container()
        created_job = Job.create(event_id, ["flood_extent", "osm_intersect", "zonal_stats"])
        container.jobs.create(created_job)
        JobService(container)._execute(created_job.job_id, False)
        finished = client.get(f"/disaster/jobs/{created_job.job_id}")
        assert finished.json()["status"] == "completed"
        assessment_id = finished.json()["assessment_id"]
        assessment = client.get(f"/disaster/assessments/{assessment_id}")
        assert assessment.status_code == 200
        kpis = assessment.json()["kpis"]
        assert "flood_area_km2" in kpis
        assert "economic_loss_inr" not in kpis
        assert kpis.get("mean_confidence") == 1.0
        mask = client.get(f"/disaster/jobs/{created_job.job_id}/mask")
        assert mask.status_code == 200
        assert mask.content[:4] in {b"II*\x00", b"MM\x00*"}
        overlay = client.get("/disaster/twin/KA-HAS-001")
        assert overlay.json()["available"] is True
        assert overlay.json()["authenticity"]
        geo = client.get(f"/disaster/assessments/{assessment_id}/geojson")
        assert geo.status_code == 200
        assert geo.json()["type"] == "FeatureCollection"
        md = client.get(f"/disaster/assessments/{assessment_id}/report?location=KA-HAS-001")
        assert md.status_code == 200
        pdf = client.get(
            f"/disaster/assessments/{assessment_id}/report?location=KA-HAS-001&fmt=pdf"
        )
        assert pdf.status_code == 200
        assert pdf.content[:4] == b"%PDF"
        js = client.get(
            f"/disaster/assessments/{assessment_id}/report?location=KA-HAS-001&fmt=json"
        )
        assert js.status_code == 200
        assert js.json()["assessment_id"] == assessment_id
        csvr = client.get(
            f"/disaster/assessments/{assessment_id}/report?location=KA-HAS-001&fmt=csv"
        )
        assert csvr.status_code == 200
        assert b"assessment_id" in csvr.content
        listed = client.get("/disaster/jobs")
        assert listed.status_code == 200
        assert listed.json()["total"] >= 1

    def test_reject_bad_upload(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        aoi = {
            "type": "Polygon",
            "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
        }
        event_id = client.post(
            "/disaster/events",
            json={"disaster_type": "flood", "aoi": aoi, "t_start": "2018-08-15T00:00:00Z"},
        ).json()["event_id"]
        bad = client.post(
            "/disaster/ingest/upload",
            files={"file": ("x.exe", b"MZ", "application/octet-stream")},
            data={"event_id": event_id, "license": "x"},
        )
        assert bad.status_code in {400, 415}

    def test_non_flood_disabled(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        aoi = {
            "type": "Polygon",
            "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
        }
        resp = client.post(
            "/disaster/events",
            json={"disaster_type": "earthquake", "aoi": aoi, "t_start": "2018-08-15T00:00:00Z"},
        )
        assert resp.status_code == 501

    def test_unknown_disaster_type_rejected(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        aoi = {
            "type": "Polygon",
            "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
        }
        resp = client.post(
            "/disaster/events",
            json={"disaster_type": "volcano", "aoi": aoi, "t_start": "2018-08-15T00:00:00Z"},
        )
        assert resp.status_code == 400

    def test_metrics_and_ttl(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        assert "disaster_inflight_jobs" in client.get("/metrics").text
        assert client.post("/disaster/admin/ttl").status_code == 200

    def test_drop_ingest(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app
        from disaster_intelligence.config import data_dir

        client = TestClient(app)
        aoi = {
            "type": "Polygon",
            "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
        }
        event_id = client.post(
            "/disaster/events",
            json={"disaster_type": "flood", "aoi": aoi, "t_start": "2018-08-15T00:00:00Z"},
        ).json()["event_id"]
        inbox = data_dir() / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        write_uint8_tiff(inbox / "drop.tif", [[10, 10], [10, 10]], width=2, height=2)
        resp = client.post(
            "/disaster/ingest/drop",
            json={"event_id": event_id, "license": "drop"},
        )
        assert resp.status_code == 201
        assert resp.json()["scene_ids"]


class TestPreprocess:
    def test_tiles_and_qc(self, tmp_path: Path) -> None:
        from disaster_intelligence.application.preprocess import (
            make_tiles,
            quality_control,
            write_geoparquet_sidecar,
        )
        from disaster_intelligence.domain.errors import ValidationError

        rows = [[1] * 10 for _ in range(10)]
        assert quality_control(rows, 200) == []
        tiles = make_tiles(rows, tile_size=8)
        assert len(tiles) == 4
        geo = tmp_path / "a.geojson"
        geo.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
        gz = write_geoparquet_sidecar(geo)
        assert Path(gz).exists()
        with pytest.raises(ValidationError):
            quality_control([], 10)

    def test_factory_rejects_unknown(self) -> None:
        from disaster_intelligence.domain.errors import TaskNotEnabledError
        from disaster_intelligence.inference.factory import create_flood_runner

        with pytest.raises(TaskNotEnabledError):
            create_flood_runner("unet-missing", 80)

    def test_road_length(self) -> None:
        from disaster_intelligence.domain.geometry import line_length_km

        geom = {
            "type": "LineString",
            "coordinates": [[76.0, 12.9], [76.01, 12.9]],
        }
        length = line_length_km(geom)
        assert length is not None and length > 0

    def test_multiline_and_envelope(self) -> None:
        from disaster_intelligence.domain.geometry import (
            envelope_intersects_bbox,
            geometry_envelope,
            line_length_km,
            polygon_area_km2,
        )

        multi = {
            "type": "MultiLineString",
            "coordinates": [[[76.0, 12.9], [76.01, 12.9]], [[76.02, 12.9], [76.03, 12.9]]],
        }
        length = line_length_km(multi)
        assert length is not None and length > 0
        env = geometry_envelope(multi)
        assert env is not None
        assert envelope_intersects_bbox(env, 75.9, 12.8, 76.1, 13.0)
        assert polygon_area_km2([[0.0, 0.0]]) is None
        assert geometry_envelope({"type": "Unknown", "coordinates": []}) is None


class TestHardening:
    def test_safe_storage_rejects_paths(self) -> None:
        from disaster_intelligence.domain.errors import ValidationError
        from disaster_intelligence.domain.paths import safe_layer_name, safe_storage_name

        with pytest.raises(ValidationError):
            safe_storage_name("../escape.tif")
        with pytest.raises(ValidationError):
            safe_layer_name("../secret")

    def test_polygon_area_positive(self) -> None:
        from disaster_intelligence.domain.geometry import polygon_area_km2

        ring = [[76.0, 12.9], [76.1, 12.9], [76.1, 13.0], [76.0, 13.0], [76.0, 12.9]]
        area = polygon_area_km2(ring)
        assert area is not None and 100 < area < 150

    def test_zonal_area_uses_polygon_not_global_mask(self) -> None:
        from disaster_intelligence.domain.zonal import zonal_stats

        mask = [[1] * 20 for _ in range(20)]
        bounds = {"west": 70.0, "east": 80.0, "south": 10.0, "north": 20.0}
        ring = [[76.0, 12.9], [76.02, 12.9], [76.02, 12.92], [76.0, 12.92], [76.0, 12.9]]
        locs = [
            {
                "type": "Feature",
                "properties": {"location_id": "KA-HAS-001", "population": 1000},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ]
        rows = zonal_stats(locs, mask, bounds, 10.0)
        assert rows[0]["flood_area_km2"] < 10.0
        assert rows[0]["flood_area_km2"] != round(400 * 10.0 * rows[0]["flood_fraction"], 4)

    def test_tiff_rejects_oversized_tags(self, tmp_path: Path) -> None:
        import struct

        from disaster_intelligence.domain.errors import ValidationError
        from disaster_intelligence.domain.geotiff import TIFF_LE, read_uint8_tiff

        buf = bytearray()
        buf += TIFF_LE
        buf += struct.pack("<I", 8)
        buf += struct.pack("<H", 4)
        for tag, value in ((256, 9000), (257, 9000), (273, 64), (279, 1)):
            buf += struct.pack("<HHII", tag, 4, 1, value)
        buf += struct.pack("<I", 0)
        path = tmp_path / "bomb.tif"
        path.write_bytes(bytes(buf) + b"\x00" * 8)
        with pytest.raises(ValidationError):
            read_uint8_tiff(path)

    def test_api_key_protects_die(
        self, isolated_die: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DIE_API_KEY", "test-die-key")
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        denied = client.get("/disaster/models")
        assert denied.status_code == 401
        ok = client.get("/disaster/models", headers={"Authorization": "Bearer test-die-key"})
        assert ok.status_code == 200
        live = client.get("/health/live")
        assert live.status_code == 200

    def test_bbox_filters_polygons(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app
        from disaster_intelligence.application.container import get_container

        client = TestClient(app)
        aoi = {
            "type": "Polygon",
            "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
        }
        event_id = client.post(
            "/disaster/events",
            json={"disaster_type": "flood", "aoi": aoi, "t_start": "2018-08-15T00:00:00Z"},
        ).json()["event_id"]
        _ = event_id
        c = get_container()
        c.vectors.write_features(
            "assess1",
            "buildings",
            [
                {
                    "type": "Feature",
                    "properties": {"id": 1},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [76.0, 12.9],
                                [76.01, 12.9],
                                [76.01, 12.91],
                                [76.0, 12.91],
                                [76.0, 12.9],
                            ]
                        ],
                    },
                }
            ],
        )
        from disaster_intelligence.domain.entities import Assessment

        c.assessments.put(
            Assessment(
                assessment_id="assess1",
                event_id="e1",
                version=1,
                job_id="j1",
                disaster_type="flood",
                model_cards={},
                layers=[],
                kpis={},
                quality_flags=[],
                authenticity="USER_UPLOAD",
            )
        )
        inside = client.get(
            "/disaster/assessments/assess1/geojson?layer=buildings&bbox=75.9,12.8,76.2,13.0"
        )
        assert inside.status_code == 200
        assert len(inside.json()["features"]) == 1
        outside = client.get("/disaster/assessments/assess1/geojson?layer=buildings&bbox=0,0,1,1")
        assert outside.json()["features"] == []

    def test_unknown_layer_rejected(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app
        from disaster_intelligence.application.container import get_container
        from disaster_intelligence.domain.entities import Assessment

        client = TestClient(app)
        get_container().assessments.put(
            Assessment(
                assessment_id="assess2",
                event_id="e1",
                version=1,
                job_id="j1",
                disaster_type="flood",
                model_cards={},
                layers=[],
                kpis={},
                quality_flags=[],
                authenticity="USER_UPLOAD",
            )
        )
        resp = client.get("/disaster/assessments/assess2/layers/not-a-real-layer")
        assert resp.status_code == 404

    def test_health_reports_disk(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        health = client.get("/health")
        assert health.json()["disk_ok"] is True
        text = client.get("/metrics").text
        assert "disaster_uploads_total" in text
        assert "disaster_disk_ok" in text

    def test_speckle_median_smooths_impulse(self) -> None:
        from disaster_intelligence.application.preprocess import speckle_median

        rows = [[10, 10, 10], [10, 255, 10], [10, 10, 10]]
        out = speckle_median(rows)
        assert out[1][1] == 10

    def test_stac_rejects_unknown_collection(self, tmp_path: Path) -> None:
        from disaster_intelligence.adapters.stac.cdse import CdseStacAdapter
        from disaster_intelligence.domain.errors import ValidationError

        adapter = CdseStacAdapter(
            "https://catalogue.dataspace.copernicus.eu/stac/search",
            tmp_path,
            ["catalogue.dataspace.copernicus.eu"],
            collection_allowlist=["sentinel-1-grd"],
        )
        with pytest.raises(ValidationError):
            adapter.search(
                {"type": "Polygon", "coordinates": []}, "2020-01-01", None, ["not-a-collection"]
            )

    def test_pairing_skips_aux_rasters(self) -> None:
        from disaster_intelligence.domain.entities import Scene
        from disaster_intelligence.domain.pairing import select_pair

        aux = Scene(
            scene_id="d1",
            provider="nasadem",
            acquired_at="2018-08-16T00:00:00Z",
            license="public",
            authenticity="REAL",
            product="elevation",
        )
        s1 = Scene(
            scene_id="a",
            provider="sentinel-1",
            acquired_at="2018-08-16T00:00:00Z",
            license="copernicus-open",
            authenticity="REAL",
        )
        pair = select_pair("e1", [aux, s1], "2018-08-15T00:00:00Z")
        assert pair.after_scene_id == "a"

    def test_learned_runner_requires_weights(self) -> None:
        from disaster_intelligence.domain.errors import TaskNotEnabledError
        from disaster_intelligence.inference.factory import create_flood_runner

        runner = create_flood_runner("unet", 80)
        with pytest.raises(TaskNotEnabledError):
            runner.mask_from_rows([[1, 2], [3, 4]])

    def test_stac_pagination_follows_next(self) -> None:
        from disaster_intelligence.adapters.stac.paginate import paginate_stac_search

        class _Resp:
            def __init__(self, payload: dict) -> None:
                self.status_code = 200
                self.content = b"{}"
                self._payload = payload

            def json(self) -> dict:
                return self._payload

        class _Client:
            def post(self, url: str, json: dict | None = None) -> _Resp:
                _ = url, json
                return _Resp(
                    {
                        "features": [{"id": "a"}],
                        "links": [
                            {
                                "rel": "next",
                                "href": "https://catalogue.dataspace.copernicus.eu/stac/search?page=2",
                            }
                        ],
                    }
                )

            def request(self, method: str, url: str) -> _Resp:
                _ = method, url
                return _Resp({"features": [{"id": "b"}], "links": []})

        feats = paginate_stac_search(
            client=_Client(),  # type: ignore[arg-type]
            search_url="https://catalogue.dataspace.copernicus.eu/stac/search",
            body={"limit": 20},
            allow={"catalogue.dataspace.copernicus.eu"},
            max_pages=5,
        )
        assert [f["id"] for f in feats] == ["a", "b"]

    def test_worldpop_and_nasadem_urls(self) -> None:
        from disaster_intelligence.adapters.catalog import nasadem, worldpop

        url = worldpop.population_url("IND", 2020)
        assert worldpop.host_allowed(url)
        assert nasadem.tile_id(12.9, 77.6) == "N12E077"
        zip_url = nasadem.hgt_zip_url(12.9, 77.6)
        assert zip_url.startswith("https://e4ftl01.cr.usgs.gov/")

    def test_stac_item_maps_sar_metadata(self) -> None:
        from disaster_intelligence.application.ingest import _scene_from_stac_item

        scene = _scene_from_stac_item(
            "e1",
            "2018-08-15T00:00:00Z",
            {
                "collection": "sentinel-1-grd",
                "properties": {
                    "datetime": "2018-08-16T00:00:00Z",
                    "platform": "sentinel-1a",
                    "sar:polarizations": ["VV", "VH"],
                    "sat:orbit_state": "descending",
                    "eo:cloud_cover": 0,
                },
            },
            "https://catalogue.dataspace.copernicus.eu/stac/x",
        )
        assert scene.provider == "sentinel-1"
        assert "pol=VV,VH" in (scene.platform or "")
        assert "orbit=descending" in (scene.platform or "")
        assert scene.cloud_pct == 0.0

    def test_security_headers_on_health(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        resp = client.get("/health/live")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_rank_prefers_sentinel1(self) -> None:
        from disaster_intelligence.domain.ranking import rank_stac_features

        ranked = rank_stac_features(
            [
                {
                    "id": "s2",
                    "collection": "sentinel-2-l2a",
                    "properties": {"datetime": "2020-02-01", "eo:cloud_cover": 1},
                },
                {
                    "id": "s1",
                    "collection": "sentinel-1-grd",
                    "properties": {"datetime": "2020-01-01", "eo:cloud_cover": 0},
                },
            ]
        )
        assert ranked[0]["id"] == "s1"

    def test_catalog_fetch_rejects_host(self, tmp_path: Path) -> None:
        from disaster_intelligence.adapters.catalog.fetch import download_allowlisted
        from disaster_intelligence.domain.errors import ValidationError

        with pytest.raises(ValidationError):
            download_allowlisted("https://example.com/x.tif", tmp_path / "x.tif")

    def test_inspect_weights_rejects_tiny(self, tmp_path: Path) -> None:
        from disaster_intelligence.domain.errors import ValidationError
        from disaster_intelligence.inference.learned import inspect_weights

        path = tmp_path / "w.bin"
        path.write_bytes(b"tiny")
        with pytest.raises(ValidationError):
            inspect_weights(path)

    def test_token_cache_skips_second_http(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from disaster_intelligence.adapters.stac import oauth

        oauth.reset_token_cache()
        calls = {"n": 0}

        class _Resp:
            status_code = 200

            def json(self) -> dict:
                return {"access_token": "tok", "expires_in": 600}

        class _Client:
            def __init__(self, timeout: float) -> None:
                _ = timeout

            def __enter__(self) -> _Client:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def post(self, *args: object, **kwargs: object) -> _Resp:
                calls["n"] += 1
                return _Resp()

        monkeypatch.setenv("CDSE_USERNAME", "u")
        monkeypatch.setenv("CDSE_PASSWORD", "p")
        monkeypatch.setattr(oauth.httpx, "Client", _Client)
        assert oauth.cdse_access_token() == "tok"
        assert oauth.cdse_access_token() == "tok"
        assert calls["n"] == 1
        oauth.reset_token_cache()

    def test_duplicate_upload_reuses_checksum(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        aoi = {
            "type": "Polygon",
            "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
        }
        event_id = client.post(
            "/disaster/events",
            json={"disaster_type": "flood", "aoi": aoi, "t_start": "2018-08-15T00:00:00Z"},
        ).json()["event_id"]
        tif = isolated_die / "dup.tif"
        write_uint8_tiff(tif, [[10, 10], [10, 10]], width=2, height=2)
        payload = tif.read_bytes()
        first = client.post(
            "/disaster/ingest/upload",
            files={"file": ("dup.tif", payload, "image/tiff")},
            data={"event_id": event_id, "license": "test"},
        )
        second = client.post(
            "/disaster/ingest/upload",
            files={"file": ("dup.tif", payload, "image/tiff")},
            data={"event_id": event_id, "license": "test"},
        )
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["scene_id"] == second.json()["scene_id"]

    def test_tiff_window_and_quality_score(self, tmp_path: Path) -> None:
        from disaster_intelligence.domain.geotiff import read_uint8_window, write_uint8_tiff
        from disaster_intelligence.domain.ranking import quality_score

        path = tmp_path / "w.tif"
        write_uint8_tiff(path, [[1, 2, 3], [4, 5, 6], [7, 8, 9]], width=3, height=3)
        window, w, h = read_uint8_window(path, 1, 1, 3, 3)
        assert (w, h) == (2, 2)
        assert window[0][0] == 5
        score = quality_score(
            {
                "collection": "sentinel-1-grd",
                "properties": {"eo:cloud_cover": 0},
            }
        )
        assert score > 0.7

    def test_openapi_script(self) -> None:
        import runpy

        ns = runpy.run_path("scripts/validate_openapi.py")
        assert ns["main"]() == 0

    def test_landsat_filename(self) -> None:
        from disaster_intelligence.application.ingest import _provider_from_filename

        assert _provider_from_filename("LC08_landsat.tif") == ("landsat", "l2")

    def test_failover_uses_second_adapter(self) -> None:
        from disaster_intelligence.adapters.stac.failover import FailoverStacAdapter
        from disaster_intelligence.domain.errors import DisasterError

        class _Bad:
            def search(self, *args: object, **kwargs: object) -> list:
                raise DisasterError("down", "STAC_ERROR")

            def download(self, href: str, dest: str) -> str:
                raise DisasterError("down", "STAC_ERROR")

        class _Good:
            def search(self, *args: object, **kwargs: object) -> list:
                return [{"id": "ok"}]

            def download(self, href: str, dest: str) -> str:
                return "abc"

        adapter = FailoverStacAdapter([_Bad(), _Good()])  # type: ignore[arg-type]
        assert adapter.search({}, "2020", None, ["sentinel-1-grd"])[0]["id"] == "ok"
        assert adapter.download("https://x", "d") == "abc"

    def test_safe_zip_and_raster_stats(self, tmp_path: Path) -> None:
        import zipfile

        from disaster_intelligence.domain.archives import safe_extract_zip
        from disaster_intelligence.domain.errors import ValidationError
        from disaster_intelligence.domain.raster_ops import raster_stats, valid_epsg, water_fraction

        zpath = tmp_path / "a.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("hello.txt", "hi")
        out = safe_extract_zip(zpath, tmp_path / "out")
        assert out[0].read_text(encoding="utf-8") == "hi"
        evil = tmp_path / "evil.zip"
        with zipfile.ZipFile(evil, "w") as zf:
            zf.writestr("../escape.txt", "no")
        with pytest.raises(ValidationError):
            safe_extract_zip(evil, tmp_path / "out2")
        stats = raster_stats([[0, 1], [1, 1]], nodata=0)
        assert stats["count"] == 3
        assert water_fraction([[1, 0], [0, 0]]) == 0.25
        assert valid_epsg("EPSG:4326")

    def test_weight_discovery(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from disaster_intelligence.inference.learned import discover_weights

        folder = tmp_path / "models"
        folder.mkdir()
        (folder / "unet-flood.onnx").write_bytes(b"x" * 80)
        monkeypatch.setenv("MODEL_WEIGHTS_DIR", str(folder))
        found = discover_weights("unet")
        assert found is not None and found.name == "unet-flood.onnx"

    def test_origin_rejected(self, isolated_die: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DIE_ALLOWED_ORIGINS", "http://localhost:8501")
        from disaster_intelligence.api.main import app

        client = TestClient(app)
        denied = client.get("/disaster/models", headers={"Origin": "http://evil.example"})
        assert denied.status_code == 403
        ok = client.get("/disaster/models", headers={"Origin": "http://localhost:8501"})
        assert ok.status_code == 200

    def test_report_geojson_and_job_status_filter(self, isolated_die: Path) -> None:
        from disaster_intelligence.api.main import app
        from disaster_intelligence.application.container import get_container
        from disaster_intelligence.domain.entities import Assessment, Job

        client = TestClient(app)
        c = get_container()
        c.assessments.put(
            Assessment(
                assessment_id="ag1",
                event_id="e1",
                version=1,
                job_id="j1",
                disaster_type="flood",
                model_cards={"flood": "s1-threshold-v0"},
                layers=[],
                kpis={"flood_area_km2": 1.0},
                quality_flags=["ok"],
                authenticity="USER_UPLOAD",
            )
        )
        geo = client.get("/disaster/assessments/ag1/report?location=KA-HAS-001&fmt=geojson")
        assert geo.status_code == 200
        assert geo.json()["type"] == "FeatureCollection"
        job = Job.create("e1", ["flood_extent"])
        job.status = "completed"
        c.jobs.create(job)
        listed = client.get("/disaster/jobs?status=completed")
        assert listed.json()["total"] >= 1


def test_jsonl_reloads_assessment_by_assessment_id_not_job_id(tmp_path: Path) -> None:
    from disaster_intelligence.adapters.storage.jsonl_store import JsonlStore

    path = tmp_path / "assessments.jsonl"
    store = JsonlStore(path)
    store.put(
        "AID",
        {
            "assessment_id": "AID",
            "event_id": "E1",
            "version": 1,
            "job_id": "JID",
            "disaster_type": "flood",
        },
    )
    reloaded = JsonlStore(path)
    assert reloaded.get("AID") is not None
    assert reloaded.get("JID") is None


def test_jsonl_reloads_location_index_by_location_id(tmp_path: Path) -> None:
    from disaster_intelligence.adapters.storage.jsonl_store import JsonlStore

    path = tmp_path / "location_index.jsonl"
    store = JsonlStore(path)
    store.put("KA-HAS-001", {"location_id": "KA-HAS-001", "assessment_id": "AID"})
    reloaded = JsonlStore(path)
    assert reloaded.get("KA-HAS-001")["assessment_id"] == "AID"
