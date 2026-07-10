# Climate Risk Assessment Methodology

## Overview

Climate risk assessment for Karnataka evaluates three primary hazard types: heat stress, flood risk, and drought risk. Each hazard is scored on a 0-100 scale with five risk categories: Very Low (0-20), Low (21-40), Moderate (41-60), High (61-80), and Severe (81-100). A composite risk score combines individual hazard scores using configurable weights.

## Heat Risk

Heat risk assessment evaluates exposure to extreme temperatures based on maximum temperature thresholds, consecutive hot days (periods exceeding 35°C for 3+ days), and seasonal temperature anomalies relative to historical norms. Weighting emphasizes temperature magnitude (40%), consecutive hot days (35%), and seasonal anomaly (25%). Early warning thresholds are triggered at 35°C for heat advisories and 40°C for heat warnings.

## Flood Risk

Flood risk assessment evaluates rainfall intensity, multi-day accumulation, and forecast uncertainty. Heavy rainfall events exceeding 100 mm/day trigger high flood risk scores. Multi-day accumulation over 3 days amplifies flood risk due to saturated ground conditions. Forecast uncertainty higher than 0.3 reduces confidence in risk estimates and produces moderate baseline scores. Weighting emphasizes rainfall intensity (50%), multi-day accumulation (30%), and forecast uncertainty (20%).

## Drought Risk

Drought risk assessment evaluates rainfall deficit relative to historical means, temperature-driven evapotranspiration, and consecutive dry days. A rainfall deficit exceeding 25% below historical mean for the season indicates moderate drought risk. Temperature anomalies amplify drought risk through increased evapotranspiration. Dry periods exceeding 15 consecutive days significantly increase drought risk scores. Weighting emphasizes rainfall deficit (50%), temperature anomaly (30%), and dry period duration (20%).

## Composite Risk

Composite risk combines heat, flood, and drought scores using equal weighting by default. Weights can be configured seasonally: flood risk weight increases during monsoon (June-September), heat risk weight increases during pre-monsoon (March-May), and drought risk weight increases during post-monsoon (October-February). The composite score determines overall climate risk level for a location.

## SHAP Explainability

SHAP (SHapley Additive exPlanations) analysis identifies which factors contribute most to risk scores. Feature importance is calculated for max_temp, rainfall, consecutive_hot_days, dry_period_days, seasonal_anomaly, and forecast_uncertainty. Positive SHAP values indicate factors increasing risk, while negative values indicate factors decreasing risk.
