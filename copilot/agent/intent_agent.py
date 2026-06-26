from __future__ import annotations

import re
from typing import Any

from copilot.models import IntentResult, IntentType


class IntentAgent:
    def classify(self, query: str) -> IntentResult:
        q = query.lower().strip()
        if not q:
            return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, raw_query=query)

        patterns: list[tuple[IntentType, float, list[str], type | None]] = [
            (IntentType.GREETING, 0.9, ["hello", "hi ", "hey", "greetings", "good morning", "good evening"], None),
            (IntentType.FORECAST, 0.85, ["forecast", "weather", "temperature", "rainfall", "rain", "will it"], None),
            (IntentType.TWIN_STATE, 0.8, ["twin state", "current state", "current condition", "status", "what is the state"], None),
            (IntentType.SCENARIO, 0.85, ["scenario", "what if", "simulate", "simulation", "if temperature"], None),
            (IntentType.RISK, 0.85, ["risk", "danger", "hazard", "heat risk", "flood risk", "drought risk", "vulnerable"], None),
            (IntentType.RAG_QUERY, 0.75, ["explain", "what is", "tell me about", "how does", "why does", "define", "what causes"], None),
            (IntentType.REPORT, 0.8, ["report", "summary", "generate report", "export", "compile"], None),
        ]

        scores: dict[IntentType, float] = {}
        for intent, base_weight, keywords, _ in patterns:
            match_count = sum(1 for kw in keywords if kw in q)
            if match_count > 0:
                scores[intent] = base_weight * 100 * (1 - 0.5 ** match_count)

        entities = self._extract_entities(q)

        if not scores:
            return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, entities=entities, raw_query=query)

        best_intent = max(scores, key=scores.get)
        confidence = min(scores[best_intent] / 100.0, 1.0)
        sub_intent = self._detect_sub_intent(q, best_intent)
        return IntentResult(intent=best_intent, confidence=round(confidence, 4), entities=entities, raw_query=query, sub_intent=sub_intent)

    def _extract_entities(self, query: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        location_match = re.search(r"in\s+([A-Za-z\s]+?)(?:\?|\.|$|\sand|\sor|\s,)", query)
        if location_match:
            loc = location_match.group(1).strip().title()
            if loc and len(loc) < 50:
                entities["location"] = loc
        days_match = re.search(r"(\d+)\s*days?", query)
        if days_match:
            entities["days"] = int(days_match.group(1))
        return entities

    def _detect_sub_intent(self, query: str, intent: IntentType) -> str | None:
        if intent == IntentType.FORECAST:
            if "temperature" in query:
                return "temperature"
            if "rain" in query:
                return "rainfall"
            return "general"
        if intent == IntentType.RISK:
            if "heat" in query:
                return "heat"
            if "flood" in query:
                return "flood"
            if "drought" in query:
                return "drought"
            return "composite"
        if intent == IntentType.SCENARIO:
            if "temperature" in query:
                return "temperature"
            if "rain" in query:
                return "rainfall"
            return "general"
        return None
