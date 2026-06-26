"""Unit tests for intent classification."""

from copilot.agent.intent_agent import IntentAgent
from copilot.models import IntentType


class TestIntentAgent:
    def setup_method(self):
        self.agent = IntentAgent()

    def test_classify_forecast(self):
        result = self.agent.classify("What is the weather forecast for tomorrow?")
        assert result.intent == IntentType.FORECAST
        assert result.confidence > 0.5

    def test_classify_rainfall(self):
        result = self.agent.classify("Will it rain in Bangalore?")
        assert result.intent == IntentType.FORECAST

    def test_classify_twin_state(self):
        result = self.agent.classify("What is the current state of the twin?")
        assert result.intent == IntentType.TWIN_STATE

    def test_classify_scenario(self):
        result = self.agent.classify("What if temperature increases by 2 degrees?")
        assert result.intent == IntentType.SCENARIO

    def test_classify_risk(self):
        result = self.agent.classify("What is the flood risk in coastal Karnataka?")
        assert result.intent == IntentType.RISK

    def test_classify_rag_query(self):
        result = self.agent.classify("Explain what causes monsoon delays")
        assert result.intent == IntentType.RAG_QUERY

    def test_classify_report(self):
        result = self.agent.classify("Generate a climate report for Mysuru")
        assert result.intent == IntentType.REPORT

    def test_classify_greeting(self):
        result = self.agent.classify("Hello, how are you?")
        assert result.intent == IntentType.GREETING

    def test_classify_unknown(self):
        result = self.agent.classify("xyzzy plugh")
        assert result.intent == IntentType.UNKNOWN

    def test_empty_query(self):
        result = self.agent.classify("")
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_extract_location(self):
        result = self.agent.classify("What is the forecast in Mysuru?")
        assert result.entities.get("location") == "Mysuru"

    def test_extract_days(self):
        result = self.agent.classify("Give me 5 day forecast")
        assert result.entities.get("days") == 5

    def test_sub_intent_forecast_temperature(self):
        result = self.agent.classify("What is the temperature?")
        assert result.sub_intent == "temperature"

    def test_sub_intent_risk_heat(self):
        result = self.agent.classify("What is the heat risk?")
        assert result.sub_intent == "heat"

    def test_low_confidence_unknown(self):
        result = self.agent.classify("xyzzy")
        assert result.intent == IntentType.UNKNOWN
