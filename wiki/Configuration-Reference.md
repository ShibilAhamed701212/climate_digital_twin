# Configuration Reference

Environment variables and files that control Version 2.1. Copy `.env.example` to `.env`.

## Climate stack

See `.env.example` for gateway, twin, forecast, risk, RAG, copilot, Ollama, and data-source flags. Climate services start with `docker compose up` and do **not** require Disaster Intelligence.

## Disaster Intelligence Engine

| Variable | Default | Role |
|---|---|---|
| `DISASTER_PORT` | `8008` | Origin bind port (Compose binds `127.0.0.1` only) |
| `DIE_API_KEY` | empty | If set, DIE origin requires `Authorization: Bearer` except `/health*` and `/metrics` |
| `RATE_LIMIT_REDIS_URL` | empty | Optional Redis for gateway rate limits (`redis://host:6379`); memory fallback |
| `DISASTER_ENGINE_URL` | `http://localhost:8008` | Gateway / facade origin |
| `DISASTER_HEALTH_URL` | unset | Optional gateway health probe; overall `/health` stays healthy if unprobed or down |
| `DISASTER_DATA_DIR` | `data/disaster` | JSONL, rasters, GeoJSON |
| `DISASTER_CONFIG_PATH` | `config/disaster_config.yaml` | AOI bounds, STAC allowlist, threshold DN |
| `DISASTER_PROXY_TIMEOUT_S` | `120` | Gateway proxy timeout |
| `TWIN_POINTER_ENABLED` | `true` | HTTP overlay pointers to twin `:8001` |
| `TWIN_SERVICE_URL` | `http://localhost:8001` | Twin overlay-pointer API |
| `MODEL_FLOOD` | `threshold` | Flood runner: `threshold` (always available). `unet` runs Sen1Floods11 U-Net only with 2-channel VV/VH + weights + torch. `segformer`/`mask2former` stay disabled unless a compatible checkpoint exists. `changeformer` is not a flood mapper |
| `MODEL_FLOOD_FALLBACK` | `none` | If `threshold`, explicit fallback when a learned flood model cannot run. Never silent |
| `MODEL_DEVICE` | `auto` | `auto` / `cpu` / `cuda` / `tensorrt` / `openvino`. Missing CUDA or optional accelerators fall back; they do not crash |
| `MODEL_RUNTIME` | `auto` | `auto` / `torch` / `onnx` / `numpy`. TensorRT and OpenVINO are optional detections |
| `MODEL_WEIGHTS_UNET` / `MODEL_UNET` | empty | Path to official Sen1Floods11 U-Net `model.pt` |
| `MODEL_WEIGHTS_SEGFORMER` / `MASK2FORMER` / `CHANGEFORMER` | empty | Optional paths; SegFormer/Mask2Former remain disabled without a compatible EO flood checkpoint |
| `GPU_ENABLED` | `false` | Advertised CUDA intent; actual CUDA still requires a working torch CUDA build |
| `MODEL_WEIGHTS_DIR` | empty | Directory scanned for `unet/` (and other) weight files |
| `FEATURE_NON_FLOOD` | `false` | Non-flood types return `501 TASK_NOT_ENABLED` |
| `FEATURE_ECONOMIC_LOSS` | `false` | Does not invent INR loss; marks unavailable when on |
| `RISK_DIE_FUSION` | `false` | Attach observed-flood metadata on risk assessments |
| `RISK_DIE_ADJUST_SCORE` | `false` | Logged; **does not** mutate flood scores in V2.1 |
| `STAC_PROVIDER` | `cdse` | `cdse`, `cmr` (NASA CMR/ASF), or `mpc` (Microsoft Planetary Computer public STAC) |
| `STAC_FAILOVER` | `false` | If true, search/download tries Planetary Computer (or CDSE) after the primary adapter fails |
| `DIE_ALLOWED_ORIGINS` | empty | If set, DIE rejects requests whose `Origin` is not in the comma-separated list |
| `CDSE_USERNAME` / `CDSE_PASSWORD` | empty | Copernicus Data Space token + raster download |
| `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD` / `EARTHDATA_TOKEN` | empty | NASA Earthdata / NASADEM / CMR downloads |
| `SH_CLIENT_ID` / `SH_CLIENT_SECRET` | empty | Sentinel Hub client-credentials token (status + client only) |
| `PLANET_API_KEY` / `MAXAR_API_KEY` / `EARTHENGINE_TOKEN` / `RADIANT_API_KEY` | empty | Commercial/GEE/Radiant slots; clients await secrets (no bundled keys) |
| `CLAMAV_HOST` / `CLAMAV_PORT` | empty / `3310` | Optional ClamAV INSTREAM scan on DIE uploads |
| `WORLD_POP_FETCH` / `NASADEM_FETCH` | `false` | Advertised intent flags; live fetch still needs credentials and allowlisted URLs |

Config files: `config/disaster_config.yaml`, `config/aoi/karnataka.geojson`, `config/aoi/location_ids.geojson`, OSM extract `data/osm/karnataka.geojson`.
