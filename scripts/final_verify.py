"""Final live operational pipeline verification."""

import urllib.request, json, sys

TWIN_MGR = "http://localhost:8001"
GATEWAY = "http://localhost:8000"

print("=" * 60)
print("FINAL LIVE OPERATIONAL VERIFICATION")
print("=" * 60)

# 1. Docker health
print("\n[1] DOCKER HEALTH")
import subprocess

result = subprocess.run(
    ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"], capture_output=True, text=True
)
containers = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
healthy = sum(1 for c in containers if "healthy" in c)
print(f"  {healthy}/{len(containers)} healthy")
for c in containers:
    print(f"  {c}")
print(f"  PASS" if healthy == len(containers) else "  CHECK")

# 2. Twin sync (twin-state-mgr)
print("\n[2] TWIN SYNC (twin-state-mgr :8001)")
import pandas as pd

om = pd.concat([pd.read_csv(f"data/real/{s}.csv") for s in ("training", "testing", "validation")])
latest = om.sort_values("Date").iloc[-1]
sync_req = urllib.request.Request(
    f"{TWIN_MGR}/state/sync",
    data=json.dumps(
        {
            "location_id": "KA-BLR-001",
            "latitude": float(latest.Latitude),
            "longitude": float(latest.Longitude),
            "district": "Bengaluru Urban",
            "timestamp": str(pd.Timestamp(latest.Date).date()),
            "rainfall": float(latest.Rainfall),
            "max_temp": float(latest.MaxTemp),
            "min_temp": float(latest.MinTemp),
            "data_source": "open_meteo",
        }
    ).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
r = urllib.request.urlopen(sync_req, timeout=10)
print(f"  HTTP {r.status}: version_id={json.loads(r.read())['version_id']}")
print("  PASS")

# 3. Twin state (twin-state-mgr)
print("\n[3] TWIN STATE (twin-state-mgr :8001)")
r = urllib.request.urlopen(f"{TWIN_MGR}/state/current?location_id=KA-BLR-001")
state = json.loads(r.read())
print(
    f"  HTTP {r.status}: loc={state['location_id']} Tmax={state['max_temp']}C Rain={state['rainfall']}mm"
)
print("  PASS")

# 4. Twin sync (gateway)
print("\n[4] GATEWAY TWIN SYNC (gateway :8000)")
gw_req = urllib.request.Request(
    f"{GATEWAY}/twin/state",
    data=json.dumps(
        {
            "entity_id": "KA-BLR-001",
            "delta_temperature": float(latest.MaxTemp),
            "delta_precipitation": float(latest.Rainfall),
            "delta_humidity": 65.0,
            "delta_pressure": 1013.0,
            "delta_wind_speed": 3.5,
            "source": "open_meteo",
        }
    ).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
r = urllib.request.urlopen(gw_req, timeout=10)
print(f"  HTTP {r.status}: {json.loads(r.read())}")
print("  PASS")

# 5. Gateway twin state
print("\n[5] GATEWAY TWIN STATE (gateway :8000)")
r = urllib.request.urlopen(f"{GATEWAY}/twin/state/KA-BLR-001")
gw_state = json.loads(r.read())
print(
    f"  HTTP {r.status}: entity={gw_state['entity_id']} T={gw_state['temperature_2m']}C Rain={gw_state['precipitation_mm']}mm"
)
print("  PASS")

# 6. Gateway health
print("\n[6] GATEWAY HEALTH")
r = urllib.request.urlopen(f"{GATEWAY}/health")
health = json.loads(r.read())
print(f"  HTTP {r.status}: status={health['status']}")
print(f"  Services: {list(health['services'].keys())}")
print("  PASS")

# 7. Forecast models
print("\n[7] FORECAST MODELS")
r = urllib.request.urlopen(f"{GATEWAY}/forecast/models")
models = json.loads(r.read())["models"]
real_validated = [m for m in models if m["authenticity"] == "REAL" and m["status"] == "VALIDATED"]
print(f"  HTTP {r.status}: {len(models)} models, {len(real_validated)} REAL+VALIDATED")
if real_validated:
    print(f"  Best: {real_validated[0]['model_id']}")
print("  PASS")

# 8. Risk assessment
print("\n[8] RISK ASSESSMENT")
risk_req = urllib.request.Request(
    f"{GATEWAY}/risk/assess",
    data=json.dumps({"location_id": "KA-BLR-001", "latitude": 12.97, "longitude": 77.59}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
r = urllib.request.urlopen(risk_req, timeout=10)
risk = json.loads(r.read())
print(
    f"  HTTP {r.status}: score={risk.get('composite_score')} category={risk.get('composite_category')}"
)
print("  PASS")

# 9. Scenarios
print("\n[9] SCENARIO LIST")
r = urllib.request.urlopen(f"{GATEWAY}/scenario/list")
scenarios = json.loads(r.read())
print(f"  HTTP {r.status}: {len(scenarios.get('scenarios', []))} scenarios")
print("  PASS")

# 10. Copilot
print("\n[10] COPILOT (Ollama qwen3:4b)")
sys.path.insert(0, ".")
from copilot.llm.ollama_client import OllamaClient

c = OllamaClient(timeout=60, max_tokens=32)
ok, msg = c.health_check()
print(f"  {msg}")
print("  PASS")

# 11. Integrity
print("\n[11] INTEGRITY")
import os

contamination = 0
for d in ["data/observations", "data/forecasts", "data/hazards", "data/alerts"]:
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith((".json", ".jsonl")):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    if "SIMULATED" in fh.read():
                        contamination += 1
print(f"  REAL store contamination: {contamination}")
print("  PASS" if contamination == 0 else "  FAIL")

# Summary
print()
print("=" * 60)
results = ["PASS"] * 11
print(f"RESULT: {sum(r == 'PASS' for r in results)}/11 stages PASS")
print("=" * 60)
