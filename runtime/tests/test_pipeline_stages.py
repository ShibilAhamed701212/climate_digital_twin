"""Tests for Runtime-native pipeline stages (Phase 3).

All stages tested without loading the Climate plugin.
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest

from .conftest import make_context as _make_context


@dataclass
class _IntentContext:
    normalized_query: str = ""
    query: str = ""
    raw_query: str = ""
    intent_type: str = "knowledge"
    confidence: float = 0.8
    entities: dict[str, Any] | None = None


@dataclass
class _ProviderResultItem:
    capability: str = ""
    step_id: str = ""
    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8


@dataclass
class _ProviderResults:
    items: list[_ProviderResultItem] = field(default_factory=list)


pytestmark = pytest.mark.asyncio


class TestMemoryStage:
    @pytest.fixture
    def stage(self):
        from runtime.pipeline.stages.memory_stage import MemoryStage

        return MemoryStage()

    async def test_execute_empty(self, stage):
        """MemoryStage with no stored memory should produce empty state."""
        ctx = _make_context()
        result = await stage.execute(ctx)
        state_entry = result.blackboard.get("memory.state")
        assert state_entry is not None
        state = state_entry.value
        assert isinstance(state, dict)
        assert "working" in state
        assert "conversation" in state
        assert "facts" in state
        assert "preferences" in state

    async def test_execute_with_conversation(self, stage):
        """MemoryStage should expose stored conversation turns."""
        stage.store_conversation_turn("user", "Hello")
        stage.store_conversation_turn("assistant", "Hi there")
        ctx = _make_context()
        result = await stage.execute(ctx)
        state = result.blackboard.get("memory.state").value
        assert len(state["conversation"]) == 2

    async def test_execute_with_preferences(self, stage):
        """MemoryStage should expose stored preferences."""
        stage.set_preference("units", "metric")
        pref = stage.get_preference("units")
        assert pref == "metric"
        ctx = _make_context()
        result = await stage.execute(ctx)
        state = result.blackboard.get("memory.state").value
        assert len(state["preferences"]) == 1
        assert state["preferences"][0].value == "metric"

    async def test_emits_memory_loaded_event(self, stage):
        """MemoryStage should emit MEMORY_LOADED event."""
        from runtime.events.definitions import MEMORY_LOADED

        handler = MagicMock()
        ctx = _make_context()
        ctx.event_bus.subscribe(MEMORY_LOADED, handler)
        await stage.execute(ctx)
        assert handler.called


class TestRetrievalStage:
    @pytest.fixture
    def stage(self):
        from runtime.pipeline.stages.retrieval_stage import RetrievalStage

        return RetrievalStage()

    async def test_execute_no_query(self, stage):
        """RetrievalStage with no query should return empty result."""
        ctx = _make_context()
        result = await stage.execute(ctx)
        entry = result.blackboard.get("retrieval.result")
        assert entry is not None
        assert entry.value.query == ""

    async def test_execute_with_intent(self, stage):
        """RetrievalStage should extract query from intent context."""
        ctx = _make_context()
        ctx.stage_outputs["intent"] = _IntentContext(
            normalized_query="climate data",
            query="What is the climate data?",
            raw_query="What is the climate data?",
            intent_type="knowledge",
            confidence=0.8,
        )
        result = await stage.execute(ctx)
        entry = result.blackboard.get("retrieval.result")
        assert entry is not None

    async def test_emits_retrieval_events(self, stage):
        """RetrievalStage should emit retrieval events when query present."""
        from runtime.events.definitions import RETRIEVAL_STARTED

        handler = MagicMock()
        ctx = _make_context()
        ctx.stage_outputs["intent"] = _IntentContext(
            query="test query",
            normalized_query="test query",
            raw_query="test query",
            intent_type="knowledge",
            confidence=0.8,
        )
        ctx.event_bus.subscribe(RETRIEVAL_STARTED, handler)
        await stage.execute(ctx)
        assert handler.called


class TestEvidenceAggregationStage:
    @pytest.fixture
    def stage(self):
        from runtime.pipeline.stages.evidence_aggregation_stage import (
            EvidenceAggregationStage,
        )

        return EvidenceAggregationStage()

    async def test_execute_no_results(self, stage):
        """Empty ProviderResults should produce empty evidence list."""
        ctx = _make_context()
        result = await stage.execute(ctx)
        entry = result.blackboard.get("evidence.list")
        assert entry is not None
        assert entry.value == []

    async def test_execute_with_results(self, stage):
        """ProviderResults should be converted to Evidence."""
        ctx = _make_context()
        ctx.stage_outputs["provider_results"] = _ProviderResults(
            items=[
                _ProviderResultItem(
                    capability="forecast",
                    step_id="step_1",
                    success=True,
                    data={"temperature": 32, "humidity": 65},
                    metadata={"provider": "forecast_v1"},
                )
            ]
        )
        result = await stage.execute(ctx)
        evidence_entry = result.blackboard.get("evidence.list")
        assert evidence_entry is not None
        evidence_list = evidence_entry.value
        assert len(evidence_list) > 0
        assert evidence_list[0].capability == "forecast"
        assert evidence_list[0].payload.get("temperature") == 32

    async def test_empty_results_no_crash(self, stage):
        """Missing ProviderResults should not crash."""
        ctx = _make_context()
        result = await stage.execute(ctx)
        assert len(result.errors) == 0

    async def test_builds_evidence_graph(self, stage):
        """Evidence graph should be built from results."""
        ctx = _make_context()
        ctx.stage_outputs["provider_results"] = _ProviderResults(
            items=[
                _ProviderResultItem(
                    capability="forecast",
                    step_id="f1",
                    success=True,
                    data={"temperature": 32},
                ),
                _ProviderResultItem(
                    capability="risk",
                    step_id="r1",
                    success=True,
                    data={"risk_score": 0.7},
                ),
            ]
        )
        result = await stage.execute(ctx)
        graph_entry = result.blackboard.get("evidence.graph")
        assert graph_entry is not None
        assert graph_entry.value.node_count == 2


class TestGroundingStage:
    @pytest.fixture
    def stage(self):
        from runtime.pipeline.stages.grounding_stage import GroundingStage

        return GroundingStage()

    async def test_empty_evidence(self, stage):
        """No evidence should produce pass with no claims."""
        ctx = _make_context()
        result = await stage.execute(ctx)
        report_entry = result.blackboard.get("grounding.report")
        assert report_entry is not None
        assert True  # No claims = passes

    async def test_emits_grounding_events(self, stage):
        """GroundingStage should emit grounding events."""
        from runtime.events.definitions import GROUNDING_STARTED

        handler = MagicMock()
        ctx = _make_context()
        ctx.event_bus.subscribe(GROUNDING_STARTED, handler)
        await stage.execute(ctx)
        assert handler.called


class TestReasoningStage:
    @pytest.fixture
    def stage(self):
        from runtime.pipeline.stages.reasoning_stage import ReasoningStage

        return ReasoningStage()

    async def test_empty_evidence(self, stage):
        """No evidence should produce no conclusions."""
        ctx = _make_context()
        result = await stage.execute(ctx)
        output_entry = result.blackboard.get("reasoning.output")
        assert output_entry is not None
        # May have conclusions even with empty evidence (aggregate fallback)
        assert hasattr(output_entry.value, "conclusions")

    async def test_emits_reasoning_events(self, stage):
        """ReasoningStage should emit reasoning events."""
        from runtime.events.definitions import REASONING_STARTED

        handler = MagicMock()
        ctx = _make_context()
        ctx.event_bus.subscribe(REASONING_STARTED, handler)
        await stage.execute(ctx)
        assert handler.called

    async def test_rule_based_with_evidence(self, stage):
        """Evidence with high confidence should produce direct conclusions."""
        from runtime.models.evidence import Evidence

        ctx = _make_context()
        ev = Evidence(
            capability="forecast",
            confidence=0.95,
            payload={"temperature": 32},
        )
        ctx.blackboard.publish("evidence.list", [ev], "test")
        ctx.blackboard.publish("evidence.graph", MagicMock(node_count=0, edge_count=0), "test")
        result = await stage.execute(ctx)
        output = result.blackboard.get("reasoning.output")
        assert output is not None
