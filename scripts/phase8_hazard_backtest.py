"""Phase 8 — Hazard backtest against full Bengaluru OM record."""

import pandas as pd
import numpy as np

train = pd.read_csv("data/real/training.csv", parse_dates=["Date"])
val = pd.read_csv("data/real/validation.csv", parse_dates=["Date"])
test = pd.read_csv("data/real/testing.csv", parse_dates=["Date"])
om = pd.concat([train, val, test]).sort_values("Date").reset_index(drop=True)
print(f"Full OM record: {len(om)} days, {om.Date.min().date()} to {om.Date.max().date()}")


def heat_score(tmax):
    if tmax <= 35:
        return 0.0
    return min(100.0, (tmax - 35.0) * 4.0)


def heavy_rain_score(rainfall):
    if rainfall <= 100:
        return (rainfall / 100.0) * 50.0
    return 50.0 + ((rainfall - 100.0) / 100.0) * 50.0


# Count events and severity breakdowns
heat_events = [
    {"date": r["Date"], "tmax": r["MaxTemp"], "score": heat_score(r["MaxTemp"])}
    for _, r in om.iterrows()
    if heat_score(r["MaxTemp"]) > 0
]

rain_events = [
    {"date": r["Date"], "rain": r["Rainfall"], "score": heavy_rain_score(r["Rainfall"])}
    for _, r in om.iterrows()
    if heavy_rain_score(r["Rainfall"]) > 0
]

# Dry spells >= 10 days
dry_runs = []
current = []
for _, r in om.iterrows():
    if r["Rainfall"] == 0:
        current.append(r["Date"])
    else:
        if len(current) >= 10:
            dry_runs.append({"start": current[0], "end": current[-1], "days": len(current)})
        current = []

print(f"\nHEAT: {len(heat_events)} events (tmax>35C)")
for label, (lo, hi) in [
    ("NONE", (0, 0)),
    ("LOW", (1, 20)),
    ("MODERATE", (21, 40)),
    ("HIGH", (41, 60)),
    ("SEVERE", (61, 100)),
]:
    cnt = sum(1 for e in heat_events if lo <= e["score"] <= hi)
    print(f"  {label}: {cnt}")
if heat_events:
    for e in sorted(heat_events, key=lambda x: x["score"], reverse=True)[:5]:
        print(f"    [{e['date'].date()}] Tmax={e['tmax']:.1f}C score={e['score']:.1f}")

print(f"\nHEAVY_RAIN: {len(rain_events)} events (rain>0mm)")
for label, (lo, hi) in [
    ("LOW", (1, 20)),
    ("MODERATE", (21, 40)),
    ("HIGH", (41, 60)),
    ("SEVERE", (61, 100)),
]:
    cnt = sum(1 for e in rain_events if lo <= e["score"] <= hi)
    print(f"  {label}: {cnt}")
if rain_events:
    for e in sorted(rain_events, key=lambda x: x["score"], reverse=True)[:5]:
        print(f"    [{e['date'].date()}] Rain={e['rain']:.1f}mm score={e['score']:.1f}")

print(f"\nDRY SPELLS (>=10 days): {len(dry_runs)}")
dry_runs.sort(key=lambda x: x["days"], reverse=True)
for dr in dry_runs[:5]:
    print(f"    {dr['start'].date()} to {dr['end'].date()}: {dr['days']} days")

# Rainfall extremes
rainfall = om["Rainfall"]
p90 = rainfall.quantile(0.90)
p95 = rainfall.quantile(0.95)
p99 = rainfall.quantile(0.99)
print(
    f"\nRainfall percentiles: p50={rainfall.median():.1f}, p90={p90:.1f}, p95={p95:.1f}, p99={p99:.1f}"
)
top10 = rainfall[rainfall >= p90]
print(f"  Events >= p90 ({p90:.1f}mm): {len(top10)}")
print(f"  Events >= p95 ({p95:.1f}mm): {sum(rainfall >= p95)}")
print(f"  Events >= p99 ({p99:.1f}mm): {sum(rainfall >= p99)}")

tmax = om["MaxTemp"]
p90_tmax = tmax.quantile(0.90)
p95_tmax = tmax.quantile(0.95)
print(f"\nTmax percentiles: p50={tmax.median():.1f}, p90={p90_tmax:.1f}, p95={p95_tmax:.1f}")
print(f"  Days >= p90 ({p90_tmax:.1f}C): {sum(tmax >= p90_tmax)}")
print(f"  Days >= 35C: {sum(tmax >= 35)}")

# Hazard detection rates at various thresholds
for thresh, label in [(30, ">30C"), (35, ">35C"), (37, ">37C")]:
    actual = sum(tmax >= thresh)
    detected = sum(1 for e in heat_events if e["tmax"] >= thresh)
    print(
        f"\nHeat detection at {label}: actual={actual}, detected={detected}, "
        f"HIT rate={detected / max(actual, 1):.1%} (expected 100%% for threshold rule)"
    )
