# Climate Digital Twin

## Overview

Climate Digital Twin is an AI-powered platform that creates a **digital replica of India's climate system** with a focus on the Karnataka region. The platform integrates real-time weather data ingestion, physics-informed coupled simulations, deep learning forecasting, multi-hazard risk assessment, and a conversational AI assistant — all accessible through a 10-page interactive dashboard and a unified REST API gateway.

## What is a Climate Digital Twin?

A **digital twin** is a virtual representation of a physical system that is continuously updated with real-world data. In the climate context, our digital twin:

1. **Observes** — Ingests real-time and historical weather data from Open-Meteo, NASA POWER, and IMD
2. **Simulates** — Runs physics-informed models (evapotranspiration, runoff, soil water balance, drought indices)
3. **Predicts** — Generates multi-horizon forecasts using an ensemble of 8 ML/statistical models
4. **Assesses** — Computes heat, flood, and drought risk scores with SHAP-based explainability
5. **Responds** — Enables what-if scenario analysis through Monte Carlo simulation
6. **Communicates** — Provides natural-language climate insights via an AI Copilot

## Key Features

- **10 Microservices** — Twin State Manager, Forecast Engine, Scenario Engine, Risk Engine, RAG Service, Copilot Agent, API Gateway, Dashboard, Report Service, Ollama LLM
- **8 Forecasting Models** — LSTM, Transformer, iTransformer, PatchTST, TimeMixer, XGBoost, Prophet, Baseline
- **Multi-Hazard Risk** — Heat, flood, drought scoring with composite risk aggregation
- **FAISS Vector Store** — Hybrid semantic + BM25 search over climate knowledge documents
- **Interactive Dashboard** — 10-page Streamlit UI with charts, maps, and real-time data
- **86% Test Coverage** — 2700+ unit and integration tests

## Quick Links

- [Installation Guide](Installation-Guide.md)
- [System Architecture](System-Architecture.md)
- [API Reference](API-Reference.md)
- [Deployment Guide](Deployment-Guide.md)
