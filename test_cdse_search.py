import httpx
import json

r = httpx.post(
    'https://stac.dataspace.copernicus.eu/v1/search',
    json={
        'collections': ['sentinel-1-grd'],
        'intersects': {
            'type': 'Polygon',
            'coordinates': [[[76.00, 12.95], [76.15, 12.95], [76.15, 13.08], [76.00, 13.08], [76.00, 12.95]]]
        },
        'datetime': '2018-08-01T00:00:00Z/2018-08-31T00:00:00Z',
        'limit': 5
    },
    timeout=60
)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Features: {len(data.get('features', []))}")
for f in data.get('features', [])[:3]:
    print(f.get('id'))