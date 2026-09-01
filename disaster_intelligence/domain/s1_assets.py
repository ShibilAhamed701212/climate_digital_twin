from __future__ import annotations

from typing import Any

from disaster_intelligence.domain.errors import ValidationError

_VV_KEYS = ("vv", "sigma0_vv", "polarisation-vv", "polarization-vv", "grd_vv")
_VH_KEYS = ("vh", "sigma0_vh", "polarisation-vh", "polarization-vh", "grd_vh")
_PRODUCT_KEYS = ("product", "data", "safe", "cog_safe")


def polarizations_from_stac(item: dict[str, Any]) -> list[str]:
    props = item.get("properties") or {}
    raw = props.get("sar:polarizations") or props.get("polarisation") or props.get("polarization")
    found: list[str] = []
    if isinstance(raw, list):
        found = [str(p).upper() for p in raw]
    elif isinstance(raw, str) and raw.strip():
        blob = raw.upper().replace("&", ",").replace("+", ",").replace(";", ",")
        found = [p.strip() for p in blob.split(",") if p.strip()]
    ident = str(item.get("id") or "")
    if "1SDV" in ident or "_DV_" in ident:
        if "VV" not in found:
            found.append("VV")
        if "VH" not in found:
            found.append("VH")
    return found


def require_vv_vh(pols: list[str]) -> None:
    have = {p.upper() for p in pols}
    if "VV" in have and "VH" in have:
        return
    raise ValidationError(
        "Sentinel-1 scene does not include both VV and VH; refusing to fabricate a channel",
        "INSUFFICIENT_POLARIZATION",
    )


def polarization_from_filename(name: str) -> str | None:
    lower = name.lower().replace("\\", "/")
    base = lower.rsplit("/", 1)[-1]
    if "-vh-" in base or "_vh_" in base or base.startswith("vh-") or "-vh." in base:
        return "VH"
    if "-vv-" in base or "_vv_" in base or base.startswith("vv-") or "-vv." in base:
        return "VV"
    return None


def _asset_hrefs(assets: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, spec in assets.items():
        if not isinstance(spec, dict):
            continue
        href = spec.get("href")
        if isinstance(href, str) and href:
            out[key.lower()] = href
    return out


def _http_href(href: str) -> bool:
    return href.startswith("https://") or href.startswith("http://")


def select_s1_assets(item: dict[str, Any]) -> dict[str, str]:
    """Pick VV+VH asset hrefs, or a single PRODUCT/SAFE zip. Never invent a missing pol."""
    require_vv_vh(polarizations_from_stac(item))
    hrefs = _asset_hrefs(item.get("assets") or {})
    vv = next((hrefs[k] for k in _VV_KEYS if k in hrefs), None)
    vh = next((hrefs[k] for k in _VH_KEYS if k in hrefs), None)
    product = next((hrefs[k] for k in _PRODUCT_KEYS if k in hrefs), None)
    if vv and vh and vv != vh and _http_href(vv) and _http_href(vh):
        return {"vv": vv, "vh": vh, "mode": "dual"}
    if product and _http_href(product):
        return {"product": product, "mode": "product"}
    if vv and vh and vv != vh:
        return {"vv": vv, "vh": vh, "mode": "dual"}
    if product:
        return {"product": product, "mode": "product"}
    for key, href in hrefs.items():
        pol = polarization_from_filename(key) or polarization_from_filename(href)
        if pol == "VV" and vv is None:
            vv = href
        elif pol == "VH" and vh is None:
            vh = href
    if vv and vh and vv != vh:
        return {"vv": vv, "vh": vh, "mode": "dual"}
    raise ValidationError(
        "STAC item has VV+VH metadata but no separate VV/VH assets and no PRODUCT zip",
        "INSUFFICIENT_POLARIZATION",
    )


def select_generic_asset(item: dict[str, Any]) -> str | None:
    assets = item.get("assets") or {}
    for key in ("data", "visual", "B04", "red"):
        spec = assets.get(key)
        if isinstance(spec, dict) and spec.get("href"):
            return str(spec["href"])
    return str(item.get("id") or "") or None
