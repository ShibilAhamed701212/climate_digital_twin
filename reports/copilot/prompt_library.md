# Prompt Library

## Overview

The Climate Copilot uses 4 prompt templates stored in `copilot/prompts/`. These templates are loaded by the `OllamaClient.generate_with_prompt_file()` method, which reads the file, applies `str.format()` substitution with runtime variables, and sends the result to the LLM.

## Prompt 1: Intent Classification

**File:** `copilot/prompts/intent.txt`

**Purpose:** Classify the user's climate-related query into one of 8 predefined intents.

**Content:**
```
Classify the user's climate-related query into one of these intents:
- forecast: weather prediction, temperature, rainfall queries
- twin_state: current digital twin state, live conditions
- scenario: what-if simulations, hypothetical climate changes
- risk: climate risk assessment, heat/flood/drought danger
- rag_query: explanatory questions about climate concepts
- report: generate climate reports or summaries
- greeting: hello, hi, greetings
- unknown: anything else

Query: {query}
Intent:
```

**Variables:**

| Variable | Source | Description |
|----------|--------|-------------|
| `{query}` | User input | Raw query string from the user |

**Usage:** This is a fallback/alternative to the keyword-based `IntentAgent.classify()` method. The current implementation uses keyword matching by default; this prompt is available for LLM-based classification.

**Expected Output:** A single line with the intent name (e.g., `forecast`, `risk`, `unknown`).

## Prompt 2: Planning

**File:** `copilot/prompts/planner.txt`

**Purpose:** Generate a step-by-step tool execution plan based on the user's intent and extracted entities.

**Content:**
```
Given the user intent and available tools, create a step-by-step plan.

Intent: {intent}
Available tools: forecast_tool, digital_twin_tool, scenario_simulator, risk_assessor, rag_retriever, report_generator
Extracted entities: {entities}

Plan the sequence of tool calls needed to fulfill this request.
```

**Variables:**

| Variable | Source | Description |
|----------|--------|-------------|
| `{intent}` | IntentAgent | Classified intent string (e.g., "forecast", "risk") |
| `{entities}` | IntentAgent | JSON dict of extracted entities (location, days, etc.) |

**Usage:** This is a fallback/alternative to the hardcoded `PlanningAgent._get_planner()` method dispatch. The current implementation uses intent-to-plan mappings in Python code.

**Expected Output:** A sequence of tool calls with parameters, one per line.

## Prompt 3: Response Generation

**File:** `copilot/prompts/generator.txt`

**Purpose:** Generate a natural, conversational response from tool execution results.

**Content:**
```
You are Climate Copilot, an AI assistant for the India Climate Digital Twin.
Generate a natural, concise response from the tool results.

User query: {query}
Intent: {intent}
Tool results: {results}

Rules:
- Use ONLY the data in tool results. Never fabricate numbers.
- Cite sources where available.
- Keep responses under 4 paragraphs. Be conversational but factual.
- For forecasts: summarize the trend (warming/cooling/dry/wet).
- For risk: state the composite risk score and category plainly.
- For scenarios: explain what the delta means in practical terms.
- For errors: acknowledge and suggest rephrasing.
```

**Variables:**

| Variable | Source | Description |
|----------|--------|-------------|
| `{query}` | User input | Original user query |
| `{intent}` | IntentAgent | Classified intent string |
| `{results}` | Executor | JSON array of tool execution results with data, success status, and errors |

**Usage:** This is the primary LLM integration point. When `OllamaClient` is available and initialized, the `ResponseGenerator._try_llm()` method loads this template, formats it with actual tool results, and sends it to `qwen3:8b`. If the LLM is unavailable, the generator falls back to template-based formatters.

**Rules enforced by the prompt:**
- No hallucination — "Use ONLY the data in tool results"
- Source attribution — "Cite sources where available"
- Conciseness — "Keep responses under 4 paragraphs"
- Intent-specific guidance — forecast trend summarization, risk score reporting, scenario interpretation
- Error handling — "acknowledge and suggest rephrasing"

**Expected Output:** 1–4 paragraphs of natural language response.

## Prompt 4: Error Handling

**File:** `copilot/prompts/error.txt`

**Purpose:** Generate a helpful error message when tool execution or processing fails.

**Content:**
```
An error occurred while processing your climate query.

Error details: {error}
Intent: {intent}
Query: {query}

Suggest the user rephrase their query or try a different question about forecasts, risks, or climate data.
```

**Variables:**

| Variable | Source | Description |
|----------|--------|-------------|
| `{error}` | Exception handler | Error message from the failed operation |
| `{intent}` | IntentAgent | Classified intent string |
| `{query}` | User input | Original user query |

**Usage:** This prompt is available for generating user-facing error messages. It acknowledges the error and provides guidance for rephrasing.

**Expected Output:** A short, helpful message suggesting alternative approaches.

## Prompt Usage Summary

| Prompt | File | Used By | LLM Required? | Fallback |
|--------|------|---------|---------------|----------|
| Intent Classification | `intent.txt` | IntentAgent (optional) | No | Keyword-based classifier |
| Planning | `planner.txt` | PlanningAgent (optional) | No | Hardcoded intent-to-plan mapping |
| Response Generation | `generator.txt` | ResponseGenerator | Yes (optional) | Template-based formatters |
| Error Handling | `error.txt` | Not currently wired | No | Static error messages |

## Prompt Quality Observations

1. **generator.txt** is the most critical prompt — it shapes all LLM-generated responses with specific rules for factual accuracy, source citation, and intent-specific formatting
2. **intent.txt** and **planner.txt** are currently unused in the default code path (the system uses pure Python implementations instead), but are available for LLM-based fallback
3. All prompts use `str.format()` variable substitution, which could fail if a variable name is misspelled or contains special characters
4. No system prompt separation — the prompts combine system instructions and user context in a single template
5. No few-shot examples — prompts rely entirely on instructions without example outputs to guide the LLM
