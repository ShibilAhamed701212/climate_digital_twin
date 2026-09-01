from __future__ import annotations

import re
from typing import Any

from copilot.models import IntentResult, IntentType

# ─── Intent keyword patterns (regex with word boundaries) ─────

_GREETING_KEYWORDS: list[str] = [
    r"\bhello\b",
    r"\bhi\b",
    r"\bhey\b",
    r"\bgreetings\b",
    r"\bgood morning\b",
    r"\bgood evening\b",
]

_FORECAST_KEYWORDS: list[str] = [
    r"\bforecasts?\b",
    r"\bweather\b",
    r"\btemperature\b",
    r"\brainfall\b",
    r"\brain\b",
    r"\bprecipitation\b",
    r"\bhumidity\b",
    r"\bwind\b",
    r"\bstorm\b",
    r"\bprediction\b",
    r"\bwill it\b",
    r"\btomorrow\b",
    r"\bnext week\b",
    r"\bweekend\b",
]

_TWIN_STATE_KEYWORDS: list[str] = [
    r"\btwin state\b",
    r"\bcurrent state\b",
    r"\bcurrent condition\b",
    r"\bstatus\b",
    r"\bwhat is the state\b",
]

_SCENARIO_KEYWORDS: list[str] = [
    r"\bscenario\b",
    r"\bwhat if\b",
    r"\bsimulat\w*\b",
    r"\bif temperature\b",
    r"\bwhat would\b",
    r"\bimagin\w*\b",
    r"\bwarming\b",
    r"\bincreased\b",
    r"\bhow would\b",
]

_RISK_KEYWORDS: list[str] = [
    r"\brisk\b",
    r"\bflood\b",
    r"\bdrought\b",
    r"\bheat\b",
    r"\bhazard\b",
    r"\bvulnerab\w*\b",
    r"\bexposure\b",
    r"\bdanger\b",
]

_RAG_KEYWORDS: list[str] = [
    r"\bexplain\b",
    r"\bwhat is\b",
    r"\bwhat are\b",
    r"\btell me\b",
    r"\bhow does\b",
    r"\bwhy does\b",
    r"\bdefine\b",
    r"\bwhat causes\b",
    r"\bcauses?\b",
    r"\bwhy\b",
    r"\bmean\b",
    r"\bdescribe\b",
    r"\blearn\b",
    r"\binformation\b",
    r"\bimpact\b",
    r"\beffect\b",
    r"\bmonsoon\b",
    r"\bclimate\b",
    r"\bpatterns?\b",
]

_DISASTER_KEYWORDS: list[str] = [
    r"\bdisaster intelligence\b",
    r"\bdamaged buildings\b",
    r"\bbuilding damage\b",
    r"\bflood extent\b",
    r"\binundation\b",
    r"\brelief plan\b",
    r"\baffected hospitals\b",
    r"\broad blockage\b",
    r"\bsatellite damage\b",
    r"\bdisaster assessment\b",
]

_REPORT_KEYWORDS: list[str] = [
    r"\breport\b",
    r"\bsummary\b",
    r"\bgenerate\b",
    r"\bexport\b",
    r"\bcompile\b",
    r"\bpdf\b",
]

_FEEDBACK_KEYWORDS: list[str] = [
    r"\bfeedback\b",
    r"\baccuracy\b",
    r"\baccurate\b",
    r"\brating\b",
    r"\breview\b",
    r"\bperformance\b",
    r"\bperforming\b",
    r"\bperform\b",
    r"\bimprove\b",
    r"\btrend\b",
    r"\bopinion\b",
    r"\bsatisfaction\b",
    r"\breliable\b",
    r"\breliability\b",
    r"\busers?\s+think\b",
    r"\bthink\s+about\b",
]

# ─── Intent base weights (from original scoring) ──────────────

_INTENT_WEIGHTS: dict[IntentType, float] = {
    IntentType.GREETING: 0.9,
    IntentType.FORECAST: 0.85,
    IntentType.TWIN_STATE: 0.8,
    IntentType.SCENARIO: 0.85,
    IntentType.RISK: 0.85,
    IntentType.RAG_QUERY: 0.75,
    IntentType.REPORT: 0.8,
    IntentType.FEEDBACK: 0.8,
    IntentType.DISASTER: 0.88,
}

# ─── Compiled patterns ────────────────────────────────────────

_INTENT_PATTERNS: dict[IntentType, list[re.Pattern[str]]] = {
    IntentType.GREETING: [re.compile(p, re.IGNORECASE) for p in _GREETING_KEYWORDS],
    IntentType.FORECAST: [re.compile(p, re.IGNORECASE) for p in _FORECAST_KEYWORDS],
    IntentType.TWIN_STATE: [re.compile(p, re.IGNORECASE) for p in _TWIN_STATE_KEYWORDS],
    IntentType.SCENARIO: [re.compile(p, re.IGNORECASE) for p in _SCENARIO_KEYWORDS],
    IntentType.RISK: [re.compile(p, re.IGNORECASE) for p in _RISK_KEYWORDS],
    IntentType.RAG_QUERY: [re.compile(p, re.IGNORECASE) for p in _RAG_KEYWORDS],
    IntentType.REPORT: [re.compile(p, re.IGNORECASE) for p in _REPORT_KEYWORDS],
    IntentType.FEEDBACK: [re.compile(p, re.IGNORECASE) for p in _FEEDBACK_KEYWORDS],
    IntentType.DISASTER: [re.compile(p, re.IGNORECASE) for p in _DISASTER_KEYWORDS],
}

# ─── Known locations ──────────────────────────────────────────

_KNOWN_LOCATIONS: set[str] = {
    "bangalore",
    "bengaluru",
    "chennai",
    "mumbai",
    "delhi",
    "new delhi",
    "kolkata",
    "hyderabad",
    "pune",
    "ahmedabad",
    "jaipur",
    "lucknow",
    "mysore",
    "mysuru",
    "kochi",
    "cochin",
    "thiruvananthapuram",
    "trivandrum",
    "bhopal",
    "chandigarh",
    "india",
    "karnataka",
    "kerala",
    "tamil nadu",
    "andhra pradesh",
    "maharashtra",
    "gujarat",
    "rajasthan",
    "west bengal",
    "uttar pradesh",
    "goa",
    "coastal",
}

_TIME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(next \w+)", re.IGNORECASE),
    re.compile(r"(this \w+)", re.IGNORECASE),
    re.compile(r"(last \w+)", re.IGNORECASE),
    re.compile(r"(tomorrow|today|yesterday)", re.IGNORECASE),
    re.compile(r"(in \d+ days?)", re.IGNORECASE),
    re.compile(r"(in \d+ weeks?)", re.IGNORECASE),
    re.compile(r"(in \d+ months?)", re.IGNORECASE),
    re.compile(r"(\d+[- ]day forecast)", re.IGNORECASE),
    re.compile(r"(\d+[- ]week forecast)", re.IGNORECASE),
]


class IntentAgent:
    def classify(self, query: str) -> IntentResult:
        q = query.lower().strip()
        if not q:
            return IntentResult(intent=IntentType.UNKNOWN, confidence=0.0, raw_query=query)

        scores: dict[IntentType, float] = {}
        match_counts: dict[IntentType, int] = {}
        for intent, patterns in _INTENT_PATTERNS.items():
            match_count = sum(1 for p in patterns if p.search(q))
            if match_count > 0:
                match_counts[intent] = match_count
                base_weight = _INTENT_WEIGHTS[intent]
                scores[intent] = base_weight * 100 * (1 - 0.5**match_count)

        entities = self._extract_entities(q)

        if not scores:
            return IntentResult(
                intent=IntentType.UNKNOWN, confidence=0.0, entities=entities, raw_query=query
            )

        best_intent = max(scores, key=scores.get)
        top_match_count = match_counts[best_intent]

        tied = [k for k, v in match_counts.items() if v == top_match_count]
        if len(tied) > 1:
            best_intent = self._break_tie(tied, q)

        confidence = min(scores[best_intent] / 100.0, 1.0)
        sub_intent = self._detect_sub_intent(q, best_intent)
        return IntentResult(
            intent=best_intent,
            confidence=round(confidence, 4),
            entities=entities,
            raw_query=query,
            sub_intent=sub_intent,
        )

    def _break_tie(self, top_intents: list[IntentType], query: str) -> IntentType:
        intent_set = set(top_intents)

        if IntentType.DISASTER in intent_set:
            return IntentType.DISASTER

        if IntentType.SCENARIO in intent_set and re.search(
            r"\bscenario\b|\bsimulat\w*\b|\bwhat if\b|\bwhat would\b", query
        ):
            return IntentType.SCENARIO

        if IntentType.RAG_QUERY in intent_set and IntentType.REPORT in intent_set:
            if re.search(r"\breport\b|\bgenerate\b|\bexport\b", query):
                return IntentType.REPORT
            return IntentType.RAG_QUERY

        if IntentType.FEEDBACK in intent_set and IntentType.FORECAST in intent_set:
            if re.search(r"\baccurate\b|\baccuracy\b|\brating\b|\bfeedback\b", query):
                return IntentType.FEEDBACK
            return IntentType.FORECAST

        if IntentType.RISK in intent_set and IntentType.RAG_QUERY in intent_set:
            if re.search(r"\brisk\b|\bflood\b|\bdrought\b|\bheat\b", query):
                return IntentType.RISK
            return IntentType.RAG_QUERY

        if IntentType.TWIN_STATE in intent_set and IntentType.RAG_QUERY in intent_set:
            if re.search(
                r"\btwin state\b|\bcurrent state\b|\bcurrent condition\b|\bstatus\b", query
            ):
                return IntentType.TWIN_STATE
            return IntentType.RAG_QUERY

        return sorted(top_intents, key=lambda x: x.value)[0]

    def _extract_entities(self, query: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        location = self._extract_location(query)
        if location:
            entities["location"] = location
        days_match = re.search(r"(\d+)\s*days?", query)
        if days_match:
            entities["days"] = int(days_match.group(1))
        timeframe = self._extract_timeframe(query)
        if timeframe:
            entities["timeframe"] = timeframe
        return entities

    def _extract_location(self, query: str) -> str | None:
        query_lower = query.strip().lower()
        sorted_locations = sorted(_KNOWN_LOCATIONS, key=len, reverse=True)
        for loc in sorted_locations:
            if re.search(rf"\b{re.escape(loc)}\b", query_lower):
                return loc.title()
        return None

    def _extract_timeframe(self, query: str) -> str | None:
        query_lower = query.strip().lower()
        for pattern in _TIME_PATTERNS:
            match = pattern.search(query_lower)
            if match:
                return match.group(1).strip()
        return None

    def _detect_sub_intent(self, query: str, intent: IntentType) -> str | None:
        if intent == IntentType.FORECAST:
            if "temperature" in query or "temp" in query:
                return "temperature"
            if "rain" in query or "rainfall" in query or "precipitation" in query:
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
