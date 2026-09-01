from __future__ import annotations

from disaster_intelligence.adapters.catalog import nasadem, worldpop
from disaster_intelligence.adapters.stac.oauth import credential_status
from disaster_intelligence.inference.factory import ENABLED_FLOOD_MODELS, LEARNED_MODELS


def public_integrations() -> dict[str, object]:
    creds = credential_status()
    return {
        "stac": {
            "cdse_search": "https://catalogue.dataspace.copernicus.eu/stac/search",
            "cdse_token": "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            "cmr_search": "https://cmr.earthdata.nasa.gov/stac",
            "mpc_search": "https://planetarycomputer.microsoft.com/api/stac/v1/search",
            "sentinel_hub_token": "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token",
        },
        "catalogs": {
            "worldpop_india_2020": worldpop.INDIA_2020_UNADJ,
            "nasadem_lpdaac": nasadem.LP_DAAC_NASADEM,
            "aws_open_data": "https://registry.opendata.aws/",
            "usgs_earthdata": "https://www.usgs.gov/centers/eros",
        },
        "credentials_configured": creds,
        "flood_models": {
            "enabled": sorted(ENABLED_FLOOD_MODELS),
            "registered_without_weights": sorted(LEARNED_MODELS),
        },
        "registration": {
            "cdse": "https://dataspace.copernicus.eu/",
            "earthdata": "https://urs.earthdata.nasa.gov/users/new",
            "sentinel_hub": "https://www.sentinel-hub.com/",
            "planetary_computer": "https://planetarycomputer.microsoft.com/",
            "planet": "https://www.planet.com/",
            "maxar": "https://www.maxar.com/",
            "gee": "https://earthengine.google.com/",
            "radiant": "https://mlhub.earth/",
        },
        "awaiting_operator_secrets": [
            name
            for name, ready in creds.items()
            if name not in {"planetary_computer", "worldpop_fetch", "nasadem_fetch"} and not ready
        ],
    }
