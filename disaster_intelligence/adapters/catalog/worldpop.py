from __future__ import annotations

from urllib.parse import urlparse

INDIA_2020_UNADJ = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020/2020/IND/ind_ppp_2020_UNadj.tif"
)
ALLOWED_HOSTS = frozenset({"data.worldpop.org"})


def population_url(iso3: str = "IND", year: int = 2020) -> str:
    iso = iso3.strip().upper()
    if iso != "IND" or year != 2020:
        raise ValueError("Only IND 2020 unconstrained WorldPop is allowlisted in V2.1")
    return INDIA_2020_UNADJ


def host_allowed(url: str) -> bool:
    return (urlparse(url).hostname or "") in ALLOWED_HOSTS
