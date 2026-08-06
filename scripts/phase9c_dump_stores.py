import os, json, sys

sys.path.insert(0, ".")

# SimulationStore
print("=== SIMULATION STORE ===")
sp = "data/simulations/runs.jsonl"
if os.path.exists(sp):
    with open(sp, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line.strip())
            rid = r.get("run_id", "?")
            auth = r.get("authenticity", "?")
            steps = len(r.get("steps", []))
            print(f"  Run {i}: id={rid} auth={auth} steps={steps}")
    print(f"  Store: {sp} ({i} entries)")

# HazardStore
print()
print("=== HAZARD STORE ===")
hp = "data/hazard/hazard_assessments.jsonl"
if os.path.exists(hp):
    with open(hp, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line.strip())
            print(
                f"  Assessment {i}: type={r.get('hazard_type', '?')} severity={r.get('severity', '?')} id={r.get('assessment_id', '?')}"
            )
    print(f"  Store: {hp} ({i} entries)")
else:
    print(f"  Store not found: {hp} (searched for hazard_assessments.jsonl)")

# TwinStore
print()
print("=== TWIN STORE ===")
tp = "data/twin_store"
if os.path.isdir(tp):
    for f in sorted(os.listdir(tp)):
        print(f"  {f}")
    vi = os.path.join(tp, "version_index.parquet")
    if os.path.exists(vi):
        import pyarrow.parquet as pq

        t = pq.read_table(vi)
        print(f"  version_index: {t.num_rows} rows")
        for ci in range(min(3, t.num_rows)):
            print(
                f"    [{ci}] entity={t.column('entity_id')[ci].as_py()} v{int(t.column('version_number')[ci].as_py())}"
            )
else:
    print(f"  Store not found: {tp}")

# ForecastStore
print()
print("=== FORECAST STORE ===")
fp = "data/forecasts/forecast_history.jsonl"
if os.path.exists(fp):
    with open(fp, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line.strip())
            print(
                f"  Forecast {i}: id={r.get('forecast_id', '?')} auth={r.get('authenticity')} model={r.get('model_id', '?')}"
            )
else:
    print(f"  Store not found: {fp}")

# ScenarioStore
print()
print("=== SCENARIO STORE ===")
scp = "data/scenarios"
if os.path.isdir(scp):
    for f in sorted(os.listdir(scp)):
        print(f"  {f}")
    for f in sorted(os.listdir(scp)):
        if f.endswith(".jsonl"):
            fp2 = os.path.join(scp, f)
            with open(fp2, encoding="utf-8") as fh:
                for i, line in enumerate(fh, 1):
                    r = json.loads(line.strip())
                    print(
                        f"  Scenario {i}: id={r.get('scenario_id', '?')} name={r.get('name', '?')} auth={r.get('authenticity', '?')}"
                    )
else:
    print(f"  Store not found: {scp}")

print()
print("=== INTEGRITY SCAN ===")
real_dirs = {
    "observations": "data/observations",
    "forecasts": "data/forecasts",
    "hazards": "data/hazards",
    "alerts": "data/alerts",
}
for label, d in real_dirs.items():
    if os.path.isdir(d):
        found = False
        for f in os.listdir(d):
            if f.endswith((".json", ".jsonl")):
                try:
                    with open(os.path.join(d, f), encoding="utf-8") as fh:
                        content = fh.read()
                        if "SIMULATED" in content:
                            print(f"  CONTAMINATION: {d}/{f}")
                            found = True
                except Exception:
                    pass
        status = "FAIL" if found else "VERIFIED"
    else:
        status = "N/A (no dir)"
    print(f"  No SIMULATED in {label}: {status}")
