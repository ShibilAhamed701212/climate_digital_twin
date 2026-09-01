# Troubleshooting

## Climate `/health` is healthy but overlays are empty

Disaster Intelligence is optional (`unprobed` / down does not fail gateway health). Start it with `docker compose --profile disaster up -d` and set `DISASTER_ENGINE_URL`.

## `401 UNAUTHORIZED` on DIE origin

Set `DIE_API_KEY` only if you want origin auth. Gateway still uses `GATEWAY_API_KEY`. Health and `/metrics` stay unauthenticated.

Gateway cannot reach `:8008`. Check `disaster-engine` health (`/health/live`) and compose profile.

## `501 TASK_NOT_ENABLED`

Non-flood disaster types are off unless `FEATURE_NON_FLOOD=true`. Unknown `MODEL_FLOOD` values are also rejected.

## `415` / `INVALID_GEOTIFF`

Uploads must be `.tif` / `.tiff` / `.cog` with TIFF magic bytes. Executables and truncated files are rejected.

## STAC search / download fails

CDSE credentials (`CDSE_USERNAME`, `CDSE_PASSWORD`) or Earthdata (`EARTHDATA_*`) and allowlisted hosts are required for live rasters. Catalog ingest can succeed without pixels; jobs fail until a local TIFF is uploaded or downloaded. `GET /disaster/integrations` reports which credential slots are set (not the secret values).

## Job stays `JOB_BUSY`

DIE runs a single in-flight job. Wait for completion or cancel.

## Overlay exists but twin climate state unchanged

Expected. Climate `TwinState` is not mutated; pointers live in the overlay-pointer store.
