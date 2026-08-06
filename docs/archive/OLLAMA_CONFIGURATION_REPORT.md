# Ollama Configuration Report — Qwen3:4b Copilot Model

Date: 2026-08-01
Project: Climate Digital Twin — ISRO BAH 2026 Challenge 5

---

## 1. Executive Summary

Successfully configured `qwen3:4b` as the default Copilot/AI model for Climate Digital Twin. The model is served via Ollama on `http://localhost:11434` and integrated through the existing `OllamaClient` provider abstraction. All existing tests pass with updated defaults.

---

## 2. Files Modified

| File | Change |
|------|--------|
| `copilot/configs/copilot.yaml:3` | `primary_model: "qwen3:4b"`, added `timeout: 120` |
| `copilot/llm/ollama_client.py:12` | `DEFAULT_MODEL = "qwen3:4b"` (was `llama3.2:3b`) |
| `copilot/llm/ollama_client.py:13` | `DEFAULT_TIMEOUT = 120.0` (was `30.0`) |
| `copilot/llm/ollama_client.py:26` | Added `os.environ.get("OLLAMA_MODEL")` support |
| `copilot/llm/ollama_client.py:29` | Added `os.environ.get("OLLAMA_TIMEOUT")` support |
| `copilot/config_loader.py:33` | `"primary_model": "qwen3:4b"` (was `llama3.2:3b`) |
| `copilot/workflows/orchestrator.py:29` | Fallback model `"qwen3:4b"` (was `llama3.2:3b`) |
| `.env.example` | Updated `LLM_MODEL`, `OLLAMA_MODEL` to `qwen3:4b`, added `OLLAMA_TIMEOUT=120` |
| `tests/unit/copilot/test_ollama_client.py:14,17` | Updated expected default model + timeout |
| `tests/unit/test_copilot_config.py:15` | Updated expected config model |

---

## 3. Configuration

### Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL (dev) / `http://ollama:11434` (docker) |
| `OLLAMA_MODEL` | `qwen3:4b` | Model name override |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
| `LLM_MODEL` | `qwen3:4b` | Generic LLM model name |

### YAML Configuration (`copilot/configs/copilot.yaml`)

```yaml
llm:
  host: "${OLLAMA_HOST:-http://localhost:11434}"
  primary_model: "qwen3:4b"
  temperature: 0.1
  max_tokens: 1024
  context_window: 8192
  timeout: 120
```

### Priority (highest to lowest)

1. Constructor argument (`model=...`)
2. Environment variable (`OLLAMA_MODEL`)
3. YAML config (`copilot.yaml` -> `llm.primary_model`)
4. Code constant (`DEFAULT_MODEL = "qwen3:4b"`)

---

## 4. Provider Architecture

```
Configuration
    |
    v
OllamaClient (copilot/llm/ollama_client.py)
    |-- base_url: from OLLAMA_HOST env or config or default
    |-- model: from OLLAMA_MODEL env or config or default
    |-- temperature: 0.1
    |-- max_tokens: 1024
    |-- timeout: 120s (from OLLAMA_TIMEOUT env or config)
    |
    |-- generate(prompt, system_prompt) -> str|None
    |-- health_check() -> (bool, str)
    |-- ensure_model() -> bool
    |
    v
Ollama HTTP API (http://localhost:11434/api/generate)
    |
    v
qwen3:4b (2.5 GB, CPU inference)
```

### Key properties:
- **Single provider**: Ollama-only, no multi-provider abstraction needed currently
- **No fallback to synthetic**: Returns `None` on failure; consumers handle gracefully
- **Health check**: Verifies both server reachability and model availability
- **Auto-pull**: `ensure_model()` can pull the model if missing

---

## 5. Live Verification

### Model Availability
```
$ ollama list
NAME         ID              SIZE      MODIFIED
qwen3:4b     359d7dd4bcda    2.5 GB    5 minutes ago
qwen3:14b    bdbd181c33f2    9.3 GB    2 weeks ago
```

### Health Check
```
Model: qwen3:4b
Base URL: http://localhost:11434
Health: True - Ollama running, model qwen3:4b available
```

### Generation Test
- **Prompt**: "Hello" — 23.1s (cold start)
- **Prompt**: "Say hello in 3 words" — 6.8s (warm, max_tokens=64)
- **Prompt**: "What is the typical monsoon pattern in Bengaluru?" — 13.0s (max_tokens=128)
- All responses returned successfully via `OllamaClient.generate()`

### Performance Note
qwen3:4b is a 2.5GB CPU-only model. Cold start (first inference after model load) takes ~23s. Warm inference takes ~7-13s. This is acceptable for an interactive Copilot but not for real-time use. Consider qwen3:14b (9.3GB) for better quality if GPU acceleration is available.

---

## 6. Test Results

| Suite | Passed | Failed |
|-------|--------|--------|
| Copilot (test_ollama_client.py) | 21 | 0 |
| Copilot (all tests) | 103 | 0 |
| Copilot config | 1 | 0 |

---

## 7. Limitations

1. **CPU-only inference**: 2.5GB model on CPU. Generation takes 7-23 seconds. Acceptable for Copilot chat but not streaming.
2. **No GPU acceleration**: Windows NVIDIA runtime not configured. Would significantly improve speed.
3. **Single provider**: Only Ollama supported. No OpenAI/Anthropic/Azure fallback. Returns clean error on Ollama unavailability.
4. **No streaming**: `stream=False` only. Responses delivered as complete text, not token-by-token.

---

## 8. Success Criteria

| Criterion | Status |
|-----------|--------|
| qwen3:4b is the default Copilot model | CONFIRMED |
| Configuration is externalized (YAML + env vars) | CONFIRMED |
| No hardcoded model names (all configurable) | CONFIRMED |
| Existing OllamaClient abstraction preserved | CONFIRMED |
| Scientific engine unchanged | CONFIRMED |
| Forecasting unchanged | CONFIRMED |
| Risk engine unchanged | CONFIRMED |
| Simulation unchanged | CONFIRMED |
| Copilot responds through Ollama | CONFIRMED |
| All existing tests pass | CONFIRMED (103/103) |

---

*Generated: 2026-08-01*
