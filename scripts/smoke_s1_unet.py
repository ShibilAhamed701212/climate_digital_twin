"""Optional live checks: CDSE search + Sen1Floods11 public VV/VH chip + U-Net.

Does not print credentials. Full CDSE GRD PRODUCT zips are often >500MB; this
script records that blocker instead of claiming a full CDSE download.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

AOI = {
    "type": "Polygon",
    "coordinates": [[[75.8, 12.8], [76.4, 12.8], [76.4, 13.2], [75.8, 13.2], [75.8, 12.8]]],
}
# Public Sen1Floods11 S1Hand chip (2-band VV/VH dB), CC-BY-4.0 dataset.
S1HAND = (
    "https://storage.googleapis.com/sen1floods11/v1.1/data/flood_events/"
    "HandLabeled/S1Hand/Bolivia_103757_S1Hand.tif"
)


def _load_dotenv() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


def cdse_search() -> dict:
    import httpx

    body = {
        "collections": ["sentinel-1-grd"],
        "intersects": AOI,
        "datetime": "2018-08-01T00:00:00Z/2018-08-31T00:00:00Z",
        "limit": 5,
    }
    urls = [
        "https://catalogue.dataspace.copernicus.eu/stac/search",
        "https://stac.dataspace.copernicus.eu/v1/search",
    ]
    last: dict = {"status": 0, "body": {}}
    with httpx.Client(timeout=45.0) as client:
        for url in urls:
            resp = client.post(url, json=body)
            try:
                body_json = resp.json()
            except Exception:
                body_json = {"raw": (resp.text or "")[:300]}
            last = {"status": resp.status_code, "body": body_json, "url": url}
            feats = (body_json or {}).get("features") if isinstance(body_json, dict) else None
            if resp.status_code == 200 and feats:
                return last
    return last


def download_s1hand(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(S1HAND, headers={"User-Agent": "climate-digital-twin-die/2.1"})
    with urllib.request.urlopen(req, context=ssl.create_default_context(), timeout=120) as resp:
        dest.write_bytes(resp.read())
    return dest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    _load_dotenv()
    print("=== CDSE STAC search (Karnataka AOI, 2018-08) ===")
    try:
        payload = cdse_search()
        print("http", payload["status"])
        feats = (payload["body"] or {}).get("features") or []
        print("features", len(feats))
        if feats:
            item = feats[0]
            print("id", item.get("id"))
            print("pols", (item.get("properties") or {}).get("sar:polarizations"))
            print("assets", sorted((item.get("assets") or {}).keys()))
            from disaster_intelligence.domain.s1_assets import select_s1_assets

            try:
                plan = select_s1_assets(item)
                print("download_plan", {k: ("..." if k != "mode" else v) for k, v in plan.items()})
            except Exception as exc:
                print("select_s1_assets", type(exc).__name__, exc)
        else:
            print("No CDSE features returned (catalogue empty, collection name, or network).")
    except Exception as exc:
        print("CDSE search failed:", type(exc).__name__, exc)

    print("=== Sen1Floods11 public VV/VH chip ===")
    dest = Path("data/disaster/tmp/Bolivia_103757_S1Hand.tif")
    try:
        download_s1hand(dest)
        print("downloaded", dest, dest.stat().st_size)
    except Exception as exc:
        print("S1Hand download failed:", exc)
        return 1

    from disaster_intelligence.preprocessing.sentinel1 import load_s1_stack

    stack = load_s1_stack(str(dest))
    if stack is None:
        print("Could not load VV/VH from chip")
        return 2
    vv, vh = stack.vv, stack.vh
    print("stack", stack.height, stack.width, "bounds", stack.bounds)

    ckpt = Path(r"D:/ClimateDigitalTwin/models/flood/unet/model.pt")
    if not ckpt.is_file():
        print("U-Net checkpoint missing")
        return 3
    os.environ["MODEL_WEIGHTS_UNET"] = str(ckpt)
    os.environ["MODEL_DEVICE"] = "cpu"
    from disaster_intelligence.inference.unet import UNetFloodRunner

    runner = UNetFloodRunner(dn_max=80)
    # Crop to 64px so CPU pytest-unsafe torch can still be used out of process.
    crop = min(512, len(vv), len(vv[0]) if vv else 0)
    vv_c = [row[:crop] for row in vv[:crop]]
    vh_c = [row[:crop] for row in vh[:crop]]
    mask = runner.mask_from_vv_vh(vv_c, vh_c)
    water = sum(v for row in mask for v in row)
    print(
        json.dumps(
            {
                "mask_hw": [len(mask), len(mask[0]) if mask else 0],
                "water_pixels": water,
                "confidence_type": runner.confidence_type,
                "softmax_margin": runner.last_confidence,
                "sha256_prefix": runner.checkpoint_sha256[:16],
                "fallback_used": runner.fallback_used,
                "device": runner.device,
            }
        )
    )
    print("NOTE: this is a Sen1Floods11 chip, not a full CDSE GRD PRODUCT download.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
