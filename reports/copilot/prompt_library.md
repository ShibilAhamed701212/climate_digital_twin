# Prompt Library

> **⚠️ All prompt templates are defined but NEVER executed through a real LLM.  
> The copilot `generator` uses template string responses, not prompt-based LLM generation.**

---

## Intent Classification Prompt

```text
You are a climate AI assistant classifier. Classify the following user query
into one of these intents: FORECAST, RISK, SCENARIO, EXPLAIN, TWIN, HELP, GREETING, UNKNOWN.

Query: {query}

Respond with exactly one intent label.
```

**Current status:** ⚠️ Not used. Intent classification is keyword-based, not LLM-based.

---

## Planner Prompt

```text
Given the user query and classified intent, create a step-by-step plan
to answer the query. List the tools needed and the parameters.

Query: {query}
Intent: {intent}

Plan:
1. ...
2. ...
```

**Current status:** ⚠️ Not used. Planner returns hardcoded tool sequence per intent.

---

## Generator Prompt

```text
You are a climate domain expert AI assistant. Answer the user's question
based on the retrieved context and forecast data. Be concise and accurate.

Context:
{retrieved_context}

Forecast Data:
{forecast_data}

User Query:
{query}

Answer:
```

**Current status:** ⚠️ Not used. Generator returns template strings.

---

## Error Handling Prompt

```text
The following error occurred while processing the user request.
Provide a helpful fallback response.

Error: {error_message}
User Query: {query}

Fallback Response:
```

**Current status:** ⚠️ Not used. Error responses are generic templates.

---

## Actual Response Generation

The current generator uses simple Python string templates:

```python
TEMPLATES = {
    "FORECAST": "The forecast for {location} shows {condition} conditions "
                "with temperatures around {temp}°C.",
    "RISK": "The {risk_type} risk level for {location} is {level}.",
    "SCENARIO": "Under the {scenario} scenario, {location} would experience "
                "{effect}.",
    "EXPLAIN": "The {risk_type} risk in {location} is primarily driven by "
               "{factor}.",
    "TWIN": "The current twin state for {location} is version {version}.",
    "HELP": "I can help with forecasts, risk assessments, scenarios, "
            "and digital twin state queries.",
    "GREETING": "Hello! I'm your Climate AI Copilot. How can I help you today?",
    "UNKNOWN": "I'm not sure how to help with that. Try asking about "
               "forecasts, risks, or scenarios.",
}
```

---

## Limitation Summary

| Prompt | Defined | Wired to LLM | Used |
|--------|---------|--------------|------|
| Intent Classification | ✅ | ❌ | ❌ (keyword-based instead) |
| Planner | ✅ | ❌ | ❌ (hardcoded plans) |
| Generator | ✅ | ❌ | ❌ (template strings) |
| Error Handling | ✅ | ❌ | ❌ (generic templates) |
