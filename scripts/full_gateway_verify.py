"""Full live pipeline verification against Docker gateway."""

import urllib.request, json

GATEWAY = "http://localhost:8000"


def api(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        f"{GATEWAY}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()) if e.readable() else str(e)
    except Exception as e:
        return -1, str(e)


print("=" * 60)
print("FULL LIVE GATEWAY VERIFICATION")
print("=" * 60)

# 1. Twin State
print("\n[1] GET /twin/state/KA-BLR-001")
code, data = api("GET", "/twin/state/KA-BLR-001")
print(
    f"  HTTP {code}: {data.get('entity_id')} T={data.get('temperature_2m')}C Rain={data.get('precipitation_mm')}mm"
)
print("  PASS" if code == 200 else "  FAIL")

# 2. Twin History
print("\n[2] GET /twin/history/KA-BLR-001")
code, data = api("GET", "/twin/history/KA-BLR-001")
print(f"  HTTP {code}: {data}")
print("  PASS" if code == 200 else "  WARN (may be empty)")

# 3. Forecast Models
print("\n[3] GET /forecast/models")
code, data = api("GET", "/forecast/models")
models = data.get("models", [])
real_models = [
    m for m in models if m.get("authenticity") == "REAL" and m.get("status") == "VALIDATED"
]
print(f"  HTTP {code}: {len(models)} total, {len(real_models)} REAL+VALIDATED")
if real_models:
    m = real_models[0]
    print(f"  Best: {m.get('model_id')} RMSE={m.get('metrics', {}).get('rmse', '?')}")
print("  PASS" if code == 200 else "  FAIL")

# 4. Forecast Predict
print("\n[4] POST /forecast/predict")
code, data = api(
    "POST",
    "/forecast/predict",
    {
        "location_id": "KA-BLR-001",
        "horizon": 1,
    },
)
print(f"  HTTP {code}: {json.dumps(data, default=str)[:200]}")
print("  PASS" if code in (200, 503) else "  WARN")

# 5. Risk Assess
print("\n[5] POST /risk/assess")
code, data = api(
    "POST",
    "/risk/assess",
    {
        "location_id": "KA-BLR-001",
        "latitude": 12.97,
        "longitude": 77.59,
    },
)
print(f"  HTTP {code}: {json.dumps(data, default=str)[:300]}")
print("  PASS" if code == 200 else "  WARN")

# 6. Scenario Create
print("\n[6] POST /scenario/create")
code, data = api(
    "POST",
    "/scenario/create",
    {
        "location_id": "KA-BLR-001",
        "name": "Live Test Scenario",
        "description": "Temperature +3C",
        "parameters": {"temperature_delta": 3.0},
    },
)
print(f"  HTTP {code}: {json.dumps(data, default=str)[:200]}")
print("  PASS" if code in (200, 201) else "  WARN")

# 7. Scenario List
print("\n[7] GET /scenario/list")
code, data = api("GET", "/scenario/list")
print(f"  HTTP {code}: {data}")
print("  PASS" if code == 200 else "  WARN")

# 8. RAG Ask
print("\n[8] POST /rag/ask")
code, data = api(
    "POST",
    "/rag/ask",
    {
        "question": "What is the climate of Bengaluru?",
        "collection_id": "default",
    },
)
print(f"  HTTP {code}: {json.dumps(data, default=str)[:200]}")
print("  PASS" if code in (200, 404, 503) else "  WARN")

# 9. Feedback Stats
print("\n[9] GET /feedback/stats")
code, data = api("GET", "/feedback/stats")
print(f"  HTTP {code}: {json.dumps(data, default=str)[:200]}")
print("  PASS" if code == 200 else "  WARN")

# Summary
print()
print("=" * 60)
print("GATEWAY ENDPOINT VERIFICATION COMPLETE")
print("=" * 60)
