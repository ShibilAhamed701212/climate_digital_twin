import sys

sys.path.insert(0, ".")
import xarray as xr, json
from climatedt.spatial.operations import generate_hazard_map, inverse_distance_weighted

ds = xr.open_dataset("data/validation/era5/data_stream-oper_stepType-instant.nc")
result = generate_hazard_map(ds)

# Show all keys
s = result["summary"]
print(f"Cells: {s['total_cells']}")
for k, v in s.items():
    if k != "total_cells":
        print(f"  {k}: {list(v.keys()) if isinstance(v, dict) else v}")

# Only get top-level info
print()
print(f"Heat cells affected: {len(result['heat_map'])}")
print(f"Rain cells affected: {len(result['rain_map'])}")
print(f"Dry cells affected: {len(result['dry_map'])}")

if result["heat_map"]:
    top = sorted(result["heat_map"], key=lambda x: x["score"], reverse=True)[:3]
    for t in top:
        print(f"  Hot: {t['location_id']} score={t['score']} {t['severity']}")

print("SPATIAL HAZARD MAP OPERATIONAL")
