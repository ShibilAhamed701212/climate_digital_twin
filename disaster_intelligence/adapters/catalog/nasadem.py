from __future__ import annotations

import math

LP_DAAC_NASADEM = "https://e4ftl01.cr.usgs.gov/MEASURES/NASADEM_HGT.001/2000.02.11/"
ALLOWED_HOSTS = frozenset({"e4ftl01.cr.usgs.gov", "data.lpdaac.earthdatacloud.nasa.gov"})


def tile_id(lat: float, lon: float) -> str:
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"{ns}{abs(int(math.floor(lat))):02d}{ew}{abs(int(math.floor(lon))):03d}"


def hgt_zip_url(lat: float, lon: float) -> str:
    tid = tile_id(lat, lon)
    return f"{LP_DAAC_NASADEM}NASADEM_HGT_{tid}.zip"
