import sys

sys.path.insert(0, ".")
from climatedt.spatial.grid_twin import load_karnataka_grid, find_nearest_cell, find_bengaluru_cell

ds = load_karnataka_grid(2021, 1)
print(f"Cells: {ds.grid_twin.cell_count}")
blr = find_bengaluru_cell()
print(f"Bengaluru: T={blr['temperature_2m']}C RH={blr['relative_humidity_pct']}%")

df = ds.grid_twin.to_dataframe()
for _, r in df.nlargest(3, "temperature_c").iterrows():
    print(f"Hot: ({r.latitude:.1f}N, {r.longitude:.1f}E) = {r.temperature_c:.1f}C")

print("GRID TWIN OPERATIONAL")
