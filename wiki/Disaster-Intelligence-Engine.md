# Disaster Intelligence Engine

Version 2.1 keeps an optional microservice (`disaster-engine`, localhost:8008) that maps Sentinel-class rasters to observed inundation and OSM impact overlays.

## How to run

Climate stack (unchanged):

```bash
docker compose up --build -d
```

With Disaster Intelligence:

```bash
docker compose --profile disaster up --build -d
```

Local origin:

```bash
set DISASTER_DATA_DIR=data/disaster
uvicorn disaster_intelligence.api.main:app --port 8008
```

The gateway reverse-proxies `/disaster/*` to the origin. Dashboard and Copilot call the gateway only.

## Twin integration

DIE is the system of record for assessments. The twin stores overlay **pointers** at `POST /overlay-pointer` on `:8001` without changing climate `TwinState` parquet.

## MVP models

- Flood: Sentinel-1-style threshold on uint8 TIFF digital numbers
- Preprocess: QC, SAR identity (no invented GRD calibration), tiles, gzip GeoJSON sidecars
- Assets: OSM GeoJSON intersection (inundation proxy, not xBD damage grades)
- Population: optional `population` property on `config/aoi/location_ids.geojson`
- Confidence: share of pixels farther than 8 DN from the threshold (not a calibrated probability)

## Feature flags

See `.env.example`: `TWIN_POINTER_ENABLED`, `RISK_DIE_FUSION`, `FEATURE_NON_FLOOD`, `FEATURE_ECONOMIC_LOSS`, `MODEL_FLOOD`, `STAC_PROVIDER`, CDSE/Earthdata/Sentinel Hub placeholders.
