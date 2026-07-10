"""Add docstrings to all empty __init__.py files based on directory name."""

import glob
import os

DOCSTRINGS = {
    "backend": "Climate Digital Twin - Backend API gateway and forecast service.",
    "backend.api": "API gateway routes and models.",
    "backend.core": "Core utilities and shared logic.",
    "backend.services": "Backend microservices (forecast, etc.).",
    "backend.services.forecast": "Forecast service - inference API and model loading.",
    "copilot": "AI Climate Copilot - intent classification, planning, tool execution, response generation.",
    "copilot.agent": "Intent classification agent - parses user queries into structured intents.",
    "copilot.api": "Copilot REST API - FastAPI application and route handlers.",
    "copilot.clients": "HTTP clients for backend microservices (forecast, risk, RAG, etc.).",
    "copilot.configs": "Copilot configuration defaults.",
    "copilot.llm": "Ollama LLM client - model interaction and response parsing.",
    "copilot.memory": "Conversation memory - buffer window management and history.",
    "copilot.planner": "Plan generation - decomposes intents into executable tool steps.",
    "copilot.prompts": "Prompt templates for intent classification, planning, and generation.",
    "copilot.reports": "Conversation report generation and export.",
    "copilot.tools": "Tool implementations - forecast, risk, scenario, RAG, and report tools.",
    "copilot.ui": "UI components for copilot interaction (future use).",
    "copilot.workflows": "Workflow orchestration - executor, generator, and orchestrator.",
    "dashboard": "Climate Digital Twin - Streamlit dashboard for visualization and interaction.",
    "dashboard.charts": "Chart components - time series, distribution, comparison, risk trends.",
    "dashboard.components": "Reusable UI components - cards, filters, sidebar.",
    "dashboard.config": "Dashboard configuration and constants.",
    "dashboard.maps": "Folium map components - climate overlay, comparison, risk heatmap.",
    "dashboard.page_views": "Dashboard page view modules (10 pages).",
    "dashboard.services": "Dashboard API client - communicates with backend gateway.",
    "dashboard.themes": "Dashboard theming (future use).",
    "knowledge": "Knowledge Base - RAG system for climate domain documents.",
    "knowledge.api": "Knowledge Base REST API - search and retrieval endpoints.",
    "knowledge.chunkers": "Document chunkers - text splitting strategies for RAG.",
    "knowledge.configs": "RAG configuration defaults.",
    "knowledge.embeddings": "Embedding models - sentence-transformers wrapper.",
    "knowledge.loaders": "Document loaders - MD, TXT, CSV, JSON file parsers.",
    "knowledge.pipelines": "Indexing pipeline - document processing and vector store population.",
    "knowledge.reports": "Indexing reports - quality metrics and statistics.",
    "knowledge.retriever": "Semantic search and context building for RAG retrieval.",
    "knowledge.vector_store": "FAISS vector store - index management and similarity search.",
    "models": "Forecasting models - 7 architectures with training, evaluation, and registry.",
    "models.baseline": "Baseline persistence model - repeats last observed values.",
    "models.configs": "Model training configuration defaults.",
    "models.ensemble": "Ensemble meta-learner - Ridge regression stacking of base models.",
    "models.itransformer": "iTransformer architecture - inverted Transformer for forecasting.",
    "models.lstm": "LSTM architecture - long short-term memory for time series.",
    "models.patchtst": "PatchTST architecture - patched time series Transformer.",
    "models.timemixer": "TimeMixer architecture - multi-scale mixing for forecasting.",
    "models.transformer": "Transformer architecture - vanilla Transformer encoder for forecasting.",
    "pipeline": "Data pipeline - download, clean, feature engineering, validation, export.",
    "pipeline.sources": "Data source connectors (NASA POWER, etc.).",
    "risk": "Climate Risk Engine - scoring, explainability, reporting.",
    "risk.api": "Risk Engine REST API - FastAPI application and contracts.",
    "risk.configs": "Risk scoring configuration defaults.",
    "risk.engine": "Risk engine - multi-risk assessment orchestration.",
    "risk.explainability": "SHAP-based explainability and insight generation.",
    "risk.models": "Risk scoring models and thresholds.",
    "risk.outputs": "Risk output storage (future use).",
    "risk.reports": "Risk report generation and export.",
    "risk.scoring": "Risk scoring modules - heat, flood, drought, composite.",
    "simulator": "Digital Twin and Scenario Simulator.",
    "simulator.api": "Twin state manager REST API.",
    "simulator.configs": "Simulator configuration defaults.",
    "simulator.engine": "Twin engine and scenario engine implementations.",
    "simulator.entities": "Climate entities - location, district state representations.",
    "simulator.events": "Event bus and event definitions for twin updates.",
    "simulator.models": "Scenario model definitions and data classes.",
    "simulator.outputs": "Simulation output generation and formatting.",
    "simulator.reports": "Simulation report generation.",
    "simulator.repository": "Parquet-based data repository for twin state storage.",
    "simulator.scenarios": "Scenario builder and scenario-specific API.",
    "simulator.services": "Twin and scenario business logic services.",
    "simulator.state_manager": "State version management and history tracking.",
    "simulator.validators": "Scenario validation rules and constraints.",
}


def main() -> None:
    count = 0
    for path_str in sorted(glob.glob("**/__init__.py", recursive=True)):
        with open(path_str) as f:
            content = f.read()
        if content.strip():
            continue
        dir_name = os.path.dirname(path_str).replace(os.sep, ".")
        if dir_name in DOCSTRINGS:
            with open(path_str, "w") as f:
                f.write(f'"""{DOCSTRINGS[dir_name]}"""\n')
            print(f"[ADDED] {path_str}")
            count += 1
        else:
            print(f"[SKIP]  {path_str} (no docstring for '{dir_name}')")

    print(f"\nAdded docstrings to {count} __init__.py files.")


if __name__ == "__main__":
    main()
