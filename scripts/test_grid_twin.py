from climatedt.spatial.grid_twin import load_karnataka_grid, find_nearest_cell, find_bengaluru_cell

ds = load_karnataka_grid(2021, 1)
print(f"Grid: {ds.grid_twin.grid_shape} = {ds.grid_twin.cell_count} cells")
print(f"Time: {len(ds.valid_time)} steps")

blr = find_bengaluru_cell()
print(
    f"Bengaluru: {blr['location_id']} T={blr['temperature_2m']}C RH={blr['relative_humidity_pct']}% Wind={blr['wind_speed_ms']}m/s"
)

mys = find_nearest_cell(ds, 12.30, 76.65)
print(f"Mysore: {mys['location_id']} T={mys['temperature_2m']}C")

mng = find_nearest_cell(ds, 12.91, 74.85)
print(f"Mangalore: {mng['location_id']} T={mng['temperature_2m']}C")

df = ds.grid_twin.to_dataframe()
hottest = df.nlargest(5, "temperature_c")
for _, r in hottest.iterrows():
    print(f"  Hot: ({r.latitude:.1f}N, {r.longitude:.1f}E) = {r.temperature_c:.1f}C")

coldest = df.nsmallest(5, "temperature_c")
for _, r in coldest.iterrows():
    print(f"  Cold: ({r.latitude:.1f}N, {r.longitude:.1f}E) = {r.temperature_c:.1f}C")

bbox = ds.grid_twin.bbox_cells(12.0, 14.0, 77.0, 79.0)
print(f"Bengaluru bbox: {len(bbox)} cells")
if bbox:
    temps = [c["temperature_2m"] for c in bbox]
    print(f"  Temp range: {min(temps):.1f} to {max(temps):.1f}C")

print()
print("GRID TWIN OPERATIONAL — 651 cells, spatial queries, bbox lookups")
