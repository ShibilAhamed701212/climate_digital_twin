# Lessons Learned

> **Hackathon Post-Mortem:** May–June 2026, ISRO BAH Challenge 5  
> **Honest retro on building a proof-of-concept in ~6 weeks**

---

## 1. Synthetic Data First Was Correct, But We Should Have Swapped Sooner

**Decision:** Generate synthetic data with `np.random.seed(42)` to develop pipeline without waiting for real API access.

**What happened:** The synthetic data approach got us to a working demo fast. But we never made the transition to real data. The API client wraps every call in try/except → synthetic fallback, which means real data ingestion was never actually tested end-to-end.

**Lesson:** Have a hard deadline for switching from synthetic to real data. Two weeks in, not two days before submission.

---

## 2. Docker Compose Works for Demos, But Local Dev Suffered

**Decision:** Containerize everything from day one.

**What happened:** Docker Compose reliably starts 8 services. But local development was painful: rebuilding images for every code change, Ollama requiring manual model pulls (8GB+), and Streamlit hot-reload being unreliable in containers.

**Lesson:** For a hackathon, use Docker for the final demo build but develop locally with virtualenvs. Docker first was premature optimization that slowed iteration.

---

## 3. Over-Scoping on Model Architectures

**Decision:** Define 7 model architectures (MLP, LSTM, Transformer, PatchTST, TimeMixer, iTransformer, Ensemble).

**What happened:** We shipped 3 trained models and 4 stubs. PatchTST, TimeMixer, and iTransformer are class definitions with no forward pass implementation. The ensemble is a bare Ridge regression wrapper. The "7 model" claim in early reports was misleading.

**Lesson:** One well-tested model beats six half-implemented ones. Should have focused on LSTM + basic ensemble only.

---

## 4. FAISS Empty Index — We Built the Kitchen But Forgot the Food

**Decision:** FAISS IndexFlatIP as vector store with 384-dim embeddings.

**What happened:** The index is initialized empty by default. `generate_answer()` never actually queries it — it returns mock responses. The document chunking pipeline works (15 docs → 30 chunks) but only runs on explicit trigger.

**Lesson:** Test the entire RAG pipeline end-to-end (ingest → index → retrieve → generate) before declaring it complete. A vector store with nothing in it is just an empty file.

---

## 5. Copilot Without an LLM Is a Chatbot Without a Brain

**Decision:** 4-stage pipeline: Intent → Plan → Execute → Generate, targeting Qwen3:8b via Ollama.

**What happened:** The pipeline architecture is clean. The intent classifier works (keyword-based). The executor dispatches to tools. But the Generate stage returns template strings, not LLM output. Qwen3:8b is declared but never called.

**Lesson:** If the core feature is an AI copilot, stub the pipeline early but wire the real LLM as soon as possible — even with a tiny model. Template responses look like a chatbot but fail the first non-trivial question.

---

## 6. Dashboard Mock Pages Were a Distraction

**Decision:** Build 10 Streamlit pages.

**What happened:** Pages 08 (Knowledge Base), 09 (Feedback), and 10 (BHAI State) are pure mock-ups with hardcoded content and no backend connectivity. They look unfinished (because they are) and take up 30% of the UI surface area.

**Lesson:** Hide incomplete features behind feature flags. A half-built page in the navigation undermines confidence in the working pages.

---

## 7. Test Claims That Don't Hold Up to Scrutiny

**Decision:** Run pytest and report results.

**What happened:** The "656 tests" claim originated from a different codebase context and was propagated through reports without verification. The actual count is 109 tests passing (dashboard-focused), with 18 known environment-dependent failures. None of the model, API, RAG, or copilot code has test coverage.

**Lesson:** Audit test counts before publishing. Differentiate between "tests that exist" and "tests that test the right things."

---

## 8. Config-Driven Design Was Worth It

**Decision:** YAML configuration files for districts, models, risk weights, scenarios.

**What happened:** This worked well. Configuration is centralized, validatable, and easy to change. Adding a new district to `config.yaml` propagates through the entire pipeline. Risk weights can be tuned without code changes.

**Lesson:** This pattern should be preserved and expanded in future iterations.

---

## 9. The Digital Twin Core Is the Strongest Component

**Decision:** Immutable `ClimateEntity` dataclass with append-only `StateManager` and EventBus pub/sub.

**What happened:** The twin design is clean and well-tested. Versioning works. EventBus patterns are solid. This is the most production-ready piece of the system.

**Lesson:** Invest in the data model and state management early. It pays dividends across every downstream component.

---

## 10. Honest Reporting From Day One Would Have Saved Time

**Decision:** Reports were written optimistically ("656 tests", "95% readiness", "production-ready").

**What happened:** The discrepancy between reported state and actual state caused confusion during handoffs. Fixing 57 inflated report files took non-trivial effort.

**Lesson:** Start with conservative claims and let data raise them. "What does the codebase actually say?" is the only question that matters.
