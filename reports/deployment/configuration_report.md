# Configuration Report

> **Configuration for synthetic-data demo mode. Real API keys not configured.**

---

## Configuration Files

| File | Format | Purpose |
|------|--------|---------|
| `config/config.yaml` | YAML | District list, data paths |
| `config/risk.yaml` | YAML | Risk scoring weights |
| `config/scenarios.yaml` | YAML | Scenario definitions |
| `config/model_config.yaml` | YAML | Model hyperparameters |
| `app/config.py` | Python | Dashboard configuration |

---

## config.yaml

```yaml
districts:
  - kalaburagi
  - vijayapura
  - bidar
  - raichur
  - yadgir
  - koppal
  - ballari
  - davanagere
  - chitradurga
  - tumakuru
  - chikkaballapura
  - kolar
  - ramanagara
  - mandya
  - mysuru

data:
  raw_path: "data/raw"
  processed_path: "data/processed"
  synthetic_path: "data/synthetic"
  documents_path: "data/documents"

api:
  host: "0.0.0.0"
  port: 8005
  log_level: "INFO"
```

---

## Configuration Validation

| Check | Implemented | Status |
|-------|-------------|--------|
| YAML parse validation | ✅ | Working |
| District existence check | ✅ | Working |
| Risk weight sum to 1.0 | ✅ | Working |
| Scenario parameter ranges | ✅ | Working |
| Environment variable presence | ❌ | Not implemented |

---

## Configuration Usage Across Services

| Service | Config File | Key Parameters |
|---------|-------------|----------------|
| Dashboard | app/config.py | District list, API URLs |
| Forecasting API | model_config.yaml | Hyperparameters |
| Scenario Engine | scenarios.yaml | Scenario definitions |
| Risk API | risk.yaml | Scoring weights |
| All services | Environment | Log level, data paths |

---

## Limitations

1. **No API keys.** Real NASA POWER/IMD/ISRO credentials not configured.
2. **No environment-specific configs.** Single config for all environments.
3. **No secrets management.** API keys would be in plaintext YAML.
4. **No schema validation.** Config errors fail at runtime, not parse time.
5. **No hot-reload.** Config changes require service restart.
