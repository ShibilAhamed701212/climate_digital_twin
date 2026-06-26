"""Climate Risk Assessment & Explainable AI module.

Computes heat, flood, drought, and composite climate risk scores.
Provides SHAP-based explainability, climate insights, and report
generation for the Digital Twin.
"""

from risk.api.contract import RiskAPI
from risk.engine.risk_engine import RiskEngine

__all__ = ["RiskEngine", "RiskAPI"]
