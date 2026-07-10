"""End-to-end integration test — execute the complete workflow.

Pipeline stages:
  Dataset → Forecast → Digital Twin → Scenario → Risk → RAG → Copilot → Dashboard

Each stage calls the actual API or module and validates output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch
import yaml

CONFIG_PATH = "models/configs/model_config.yaml"
with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

n_features = len(config["data"]["feature_columns"])
n_targets = len(config["data"]["target_columns"])
seq_len = config["data"]["sequence_length"]

results = []


def stage(name: str, status: str, detail: str = ""):
    results.append({"stage": name, "status": status, "detail": detail})
    icon = "PASS" if status == "OK" else "FAIL"
    print(f"  [{icon}] {name:40s} {detail}")


# ═══════════════════════════════════════════════════════════════
# 1. DATASET — Load processed data
# ═══════════════════════════════════════════════════════════════
print("\n=== 1. DATASET ===")
try:
    import pandas as pd

    train = pd.read_csv("data/processed/training.csv", nrows=100)
    val = pd.read_csv("data/processed/validation.csv", nrows=100)
    test = pd.read_csv("data/processed/testing.csv", nrows=100)
    feat_cols = config["data"]["feature_columns"]
    tgt_cols = config["data"]["target_columns"]
    for c in feat_cols + tgt_cols:
        assert c in train.columns, f"Missing feature column: {c}"
    stage("Load processed data", "OK", f"train={len(train)}, val={len(val)}, test={len(test)}")
    stage("Feature columns present", "OK", f"{len(feat_cols)} features, {len(tgt_cols)} targets")
except Exception as e:
    stage("Dataset", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 2. FORECAST — Load model and run inference
# ═══════════════════════════════════════════════════════════════
print("\n=== 2. FORECAST ===")
try:
    from models.transformer.model import TransformerModel

    model = TransformerModel(n_features=n_features, n_targets=n_targets)
    ckpt = torch.load(
        "models/checkpoints/transformer_best.pt", map_location="cpu", weights_only=True
    )
    model.load_state_dict(ckpt)
    model.eval()
    dummy_input = torch.randn(1, seq_len, n_features)
    with torch.no_grad():
        preds = model(dummy_input)
    assert preds.shape == (1, n_targets), f"Expected (1,{n_targets}), got {preds.shape}"
    stage("Load Transformer model", "OK", f"checkpoint loaded, pred shape={preds.shape}")
    print(
        f"    Predictions: rainfall={preds[0, 0]:.2f}, max_temp={preds[0, 1]:.2f}, min_temp={preds[0, 2]:.2f}"
    )
except Exception as e:
    stage("Forecast", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 3. DIGITAL TWIN — Create entity, ingest, query
# ═══════════════════════════════════════════════════════════════
print("\n=== 3. DIGITAL TWIN ===")
try:
    from simulator.engine.twin_engine import DigitalTwinEngine
    from simulator.entities.climate_entity import ClimateEntity

    engine = DigitalTwinEngine()
    entity = ClimateEntity(
        location_id="KA-E2E-001",
        latitude=15.3,
        longitude=76.0,
        district="Test",
        rainfall=50.0,
        max_temp=32.0,
        min_temp=20.0,
    )
    result = engine.ingest_observation(entity)
    assert "version_id" in result, f"Missing version_id in {result}"
    state = engine.get_current_state("KA-E2E-001")
    assert state is not None, "Current state should not be None"
    assert abs(state["rainfall"] - 50.0) < 0.01, f"Unexpected rainfall: {state['rainfall']}"
    stage("Create entity + ingest", "OK", f"version={result['version_id']}")
    stage("Query current state", "OK", f"rainfall={state['rainfall']}, temp={state['max_temp']}")

    forecast_entity = entity.update_state(rainfall=60.0, max_temp=34.0, min_temp=22.0)
    f_result = engine.apply_forecast(forecast_entity)
    stage("Apply forecast", "OK", f"version={f_result['version_id']}")

    hist = engine.get_historical_state("KA-E2E-001")
    stage("Historical states", "OK", f"{len(hist)} states")
except Exception as e:
    stage("Digital Twin", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 4. SCENARIO ENGINE — Create scenario, simulate
# ═══════════════════════════════════════════════════════════════
print("\n=== 4. SCENARIO ENGINE ===")
try:
    from simulator.engine.scenario_engine import ScenarioEngine
    from simulator.models.scenario_models import ScenarioDefinition

    scen_engine = ScenarioEngine()
    scenario = ScenarioDefinition(
        scenario_id="e2e-test",
        name="E2E Test Scenario",
        description="End-to-end temperature increase test",
        scenario_type="temperature",
        parameters={"temperature_delta": 2.0},
    )
    baseline = [
        {
            "location_id": "KA-E2E-001",
            "rainfall": 50.0,
            "max_temp": 32.0,
            "min_temp": 20.0,
            "risk_score": 25.0,
        }
    ]
    run = scen_engine.run_simulation(scenario, baseline)
    assert run.status == "completed", f"Status: {run.status}"
    result = run.results[0]
    assert result.success, f"Sim failed: {result.error_message}"
    assert result.deltas.get("max_temp", 0) > 1.5, f"Delta too small: {result.deltas}"
    stage("Create scenario", "OK", f"id={scenario.scenario_id}")
    stage("Run simulation", "OK", f"deltas: {result.deltas}")
except Exception as e:
    stage("Scenario Engine", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 5. RISK ENGINE — Assess risk for a location
# ═══════════════════════════════════════════════════════════════
print("\n=== 5. RISK ENGINE ===")
try:
    from risk.engine.risk_engine import RiskEngine

    risk_engine = RiskEngine()
    report = risk_engine.assess_all(
        location_id="KA-E2E-001",
        district="Test",
        max_temp=38.0,
        min_temp=22.0,
        rainfall=10.0,
        historical_mean_rainfall=100.0,
        historical_mean_temp=28.0,
        consecutive_hot_days=5,
        dry_period_days=20,
        seasonal_anomaly=2.5,
        forecast_uncertainty=0.2,
        prediction_confidence=0.8,
    )
    assert report.composite_risk is not None, "No composite risk"
    assert 0 <= report.composite_risk.score <= 100, f"Invalid score: {report.composite_risk.score}"
    stage(
        "Assess all risks",
        "OK",
        f"heat={report.heat_risk.score:.0f} flood={report.flood_risk.score:.0f} "
        f"drought={report.drought_risk.score:.0f} composite={report.composite_risk.score:.0f}",
    )
    assert len(report.insights) > 0, "No insights generated"
    stage("Risk insights", "OK", f"{len(report.insights)} insights")
except Exception as e:
    stage("Risk Engine", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 6. RAG RETRIEVAL — Search knowledge base
# ═══════════════════════════════════════════════════════════════
print("\n=== 6. RAG RETRIEVAL ===")
try:
    from knowledge.config_loader import load_rag_config
    from knowledge.retriever.semantic_search import SemanticSearch

    config_rag = load_rag_config()
    searcher = SemanticSearch(config=config_rag)
    queries = [
        "karnataka rainfall",
        "flood risk assessment",
        "INSAT satellite data",
    ]
    for q in queries:
        results_rag = searcher.search(q, top_k=2)
        assert len(results_rag) > 0, f"No results for: {q}"
        stage(
            f"Search: {q}",
            "OK",
            f"{len(results_rag)} results, top score={results_rag[0].score:.3f}",
        )
except Exception as e:
    stage("RAG Retrieval", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 7. CLIMATE COPILOT — Tool query
# ═══════════════════════════════════════════════════════════════
print("\n=== 7. CLIMATE COPILOT ===")
try:
    from copilot.tools.rag_tool import RAGRetrieverTool

    tool = RAGRetrieverTool()
    # Test RAG tool with a query
    try:
        result = tool.run(query="What is the rainfall pattern in Karnataka?")
        assert result is not None, "No result from RAG tool"
        is_fallback = result.get("fallback", False)
        detail = f"{len(result.get('results',[]))} results"
        if is_fallback:
            detail += " (fallback)"
        stage("RAG Tool query", "OK", detail)
    except Exception as e:
        stage("RAG Tool query", "FAIL", str(e))
except Exception as e:
    stage("Copilot (import)", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# 8. DASHBOARD — Import verification
# ═══════════════════════════════════════════════════════════════
print("\n=== 8. DASHBOARD ===")
try:
    # Verify all dashboard pages import
    import importlib
    page_modules = []
    for page_file in ["01_climate_overview", "02_forecast_viewer", "03_twin_state",
                      "04_scenario_simulator", "05_climate_risk"]:
        mod = importlib.import_module(f"dashboard.page_views.{page_file}")
        page_modules.append(mod)

    stage("Dashboard pages import", "OK", f"{len(page_modules)} pages loaded")
    # Verify folium map creation
    import folium

    m = folium.Map(location=[15.3, 76.0], zoom_start=7)
    stage("Folium map creation", "OK", "map created")
except Exception as e:
    stage("Dashboard", "FAIL", str(e))

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("END-TO-END TEST SUMMARY")
print("=" * 60)
ok = sum(1 for r in results if r["status"] == "OK")
fail = sum(1 for r in results if r["status"] == "FAIL")
for r in results:
    print(f"  [{r['status']}] {r['stage']:40s} {r['detail']}")
print(f"\n  {ok}/{len(results)} stages passed, {fail} failed")
print()
