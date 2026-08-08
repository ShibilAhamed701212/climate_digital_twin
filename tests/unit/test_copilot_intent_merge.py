"""Tests for the BHAI-merged IntentClassifier improvements."""

from __future__ import annotations

import pytest

from copilot.agent.intent_agent import IntentAgent
from copilot.models import IntentType


class TestBHAIIntentMerge:
    """Test suite for BHAI intent classification improvements."""

    @pytest.fixture
    def agent(self) -> IntentAgent:
        return IntentAgent()

    def test_classify_risk_assessment(self, agent: IntentAgent) -> None:
        queries = [
            "What's the flood risk in Bangalore?",
            "How high is heat risk in Chennai?",
            "Assess drought risk for Mysore",
            "What is the composite risk score for Delhi?",
            "Risk assessment for coastal areas",
        ]
        for query in queries:
            result = agent.classify(query)
            assert result.intent == IntentType.RISK, f"Failed for: {query}"

    def test_classify_forecast(self, agent: IntentAgent) -> None:
        queries = [
            "What will the temperature be next week?",
            "Forecast for Bangalore tomorrow",
            "What's the weather prediction for Chennai?",
            "Will it rain this weekend?",
            "Temperature forecast for next 7 days",
        ]
        for query in queries:
            result = agent.classify(query)
            assert result.intent == IntentType.FORECAST, f"Failed for: {query}"

    def test_classify_scenario(self, agent: IntentAgent) -> None:
        queries = [
            "What if temperature rises by 2 degrees?",
            "Simulate a flood scenario for Mumbai",
            "What would happen with 3 degrees warming?",
            "Run a drought scenario for Karnataka",
            "How would increased rainfall affect Chennai?",
        ]
        for query in queries:
            result = agent.classify(query)
            assert result.intent == IntentType.SCENARIO, f"Failed for: {query}"

    def test_classify_knowledge(self, agent: IntentAgent) -> None:
        queries = [
            "Tell me about monsoon patterns",
            "What causes urban flooding?",
            "Explain heat island effect",
            "How does climate change affect rainfall?",
            "What are the impacts of global warming?",
        ]
        for query in queries:
            result = agent.classify(query)
            assert result.intent == IntentType.RAG_QUERY, f"Failed for: {query}"

    def test_classify_feedback(self, agent: IntentAgent) -> None:
        queries = [
            "How accurate are the predictions?",
            "What do users think about the forecasts?",
            "Show me feedback trends",
            "How is the model performing?",
            "What's the rating for Bangalore predictions?",
        ]
        for query in queries:
            result = agent.classify(query)
            assert result.intent == IntentType.FEEDBACK, f"Failed for: {query}"

    def test_classify_report(self, agent: IntentAgent) -> None:
        queries = [
            "Generate a risk report for Mysore",
            "Create a climate report for Karnataka",
            "Export a PDF report of recent forecasts",
            "Show me the weekly report",
            "Generate a summary report for last month",
        ]
        for query in queries:
            result = agent.classify(query)
            assert result.intent == IntentType.REPORT, f"Failed for: {query}"

    def test_classify_general(self, agent: IntentAgent) -> None:
        queries = [
            "What can you do?",
            "Hello",
            "Who are you?",
            "What's your name?",
            "Thanks for your help",
            "Good morning",
        ]
        for query in queries:
            result = agent.classify(query)
            assert (
                result.intent == IntentType.UNKNOWN or result.intent == IntentType.GREETING
            ), f"Failed for: {query}"

    def test_extract_location(self, agent: IntentAgent) -> None:
        result = agent.classify("What's the risk in Bangalore?")
        assert result.entities.get("location") == "Bangalore"
        result = agent.classify("Chennai flood risk")
        assert result.entities.get("location") == "Chennai"
        result = agent.classify("How is the weather in New Delhi?")
        assert result.entities.get("location") == "New Delhi"
        result = agent.classify("Hello")
        assert result.entities.get("location") is None

    def test_extract_timeframe(self, agent: IntentAgent) -> None:
        result = agent.classify("Forecast for next week")
        assert result.entities.get("timeframe") == "next week"
        result = agent.classify("Tomorrow's weather")
        assert (
            result.entities.get("timeframe") == "tomorrow"
            or result.entities.get("timeframe") is not None
        )
        result = agent.classify("Risk for this month")
        assert result.entities.get("timeframe") == "this month"
        result = agent.classify("Hello")
        assert result.entities.get("timeframe") is None

    def test_classify_accuracy(self, agent: IntentAgent) -> None:
        test_cases = [
            ("What's the flood risk in Bangalore?", IntentType.RISK),
            ("How high is heat risk in Mumbai?", IntentType.RISK),
            ("Assess drought for Chennai", IntentType.RISK),
            ("What will the temperature be tomorrow?", IntentType.FORECAST),
            ("Forecast for next 7 days", IntentType.FORECAST),
            ("What if temperature rises by 2 degrees?", IntentType.SCENARIO),
            ("Simulate increased rainfall", IntentType.SCENARIO),
            ("Run a drought scenario for Karnataka", IntentType.SCENARIO),
            ("Tell me about monsoon patterns", IntentType.RAG_QUERY),
            ("Explain urban heat island effect", IntentType.RAG_QUERY),
            ("What causes urban flooding?", IntentType.RAG_QUERY),
            ("How accurate are the predictions?", IntentType.FEEDBACK),
            ("Generate a risk report for Mysore", IntentType.REPORT),
            ("Create a climate report for Karnataka", IntentType.REPORT),
            ("Hello, what can you do?", IntentType.UNKNOWN),
            ("Thanks!", IntentType.UNKNOWN),
            ("What is the composite risk for coastal Kerala?", IntentType.RISK),
            ("Weather prediction for next weekend", IntentType.FORECAST),
            ("Run a what-if scenario with 3C warming", IntentType.SCENARIO),
            ("What causes flooding in cities?", IntentType.RAG_QUERY),
            ("Show me feedback trends for last quarter", IntentType.FEEDBACK),
            ("Create a PDF report of climate data", IntentType.REPORT),
            ("Who built this system?", IntentType.UNKNOWN),
        ]

        correct = 0
        for query, expected in test_cases:
            result = agent.classify(query)
            if result.intent == expected:
                correct += 1

        accuracy = correct / len(test_cases)
        assert accuracy >= 0.90, f"Accuracy {accuracy:.0%} < 90%, got {correct}/{len(test_cases)}"

    def test_empty_query(self, agent: IntentAgent) -> None:
        result = agent.classify("")
        assert result.intent == IntentType.UNKNOWN
        result = agent.classify("   ")
        assert result.intent == IntentType.UNKNOWN

    def test_case_insensitivity(self, agent: IntentAgent) -> None:
        result = agent.classify("FLOOD RISK IN BANGALORE")
        assert result.intent == IntentType.RISK
        result = agent.classify("what if temperature rises")
        assert result.intent == IntentType.SCENARIO
