import urllib.request, json

endpoints = [
    "/health",
    "/twin/state/KA-BLR-001",
    "/forecast/models",
]
for ep in endpoints:
    try:
        r = urllib.request.urlopen(f"http://localhost:8000{ep}", timeout=10)
        print(f"{ep}: {r.status} -> {json.dumps(json.loads(r.read()), indent=2)[:200]}")
    except Exception as e:
        print(f"{ep}: {type(e).__name__}: {str(e)[:80]}")
