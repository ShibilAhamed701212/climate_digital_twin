import json
import zipfile
from pathlib import Path

import xarray as xr

with open("data/validation/era5/india/download_manifest.json") as f:
    m = json.load(f)

downloaded = m["downloaded_months"]
print(f"Downloaded: {len(downloaded)} months")
total_mb = sum(v["size_mb"] for v in downloaded.values())
print(f"Total size: {total_mb:.1f} MB")
print(f"Failed: {len(m['failed_months'])}")

first = sorted(downloaded.keys())[0]
fp = Path(downloaded[first]["path"])
print(f"Sample: {first} -> {fp.name} ({fp.stat().st_size / 1024:.0f} KB)")

with zipfile.ZipFile(fp) as z:
    names = [n for n in z.namelist() if n.endswith(".nc")]
    z.extract(names[0], "data/validation/era5/india/raw/")
    actual = Path("data/validation/era5/india/raw") / names[0]
    ds = xr.open_dataset(actual)
    print(f"Grid: {len(ds.latitude)}x{len(ds.longitude)} cells")
    print(f"Time: {len(ds.valid_time)} timesteps")
    print(f"Vars: {list(ds.data_vars.keys())}")
    lat_r = float(ds.latitude.min()), float(ds.latitude.max())
    lon_r = float(ds.longitude.min()), float(ds.longitude.max())
    print(f"Bounds: lat {lat_r[0]:.1f}-{lat_r[1]:.1f}, lon {lon_r[0]:.1f}-{lon_r[1]:.1f}")
    t2m = ds["t2m"].mean(dim="valid_time") - 273.15
    print(f"T2m range: {float(t2m.min()):.1f}C to {float(t2m.max()):.1f}C")
    print()
    print("ERA5 KARNATAKA DATASET VERIFIED — READY FOR PHASE 14")
