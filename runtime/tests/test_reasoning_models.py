"""Tests for Reasoning models."""


from runtime.models.reasoning import (
    Assumption,
    Conclusion,
    ConclusionType,
    ReasoningOutput,
    ReasoningStrategy,
    Unknown,
)


class TestConclusion:
    def test_create_conclusion(self):
        c = Conclusion(
            statement="Temperature is 32C",
            confidence=0.9,
            conclusion_type=ConclusionType.DIRECT,
            supporting_evidence_ids=["ev_001"],
        )
        assert c.statement == "Temperature is 32C"
        assert c.confidence == 0.9
        assert c.conclusion_type == ConclusionType.DIRECT

    def test_inferred_conclusion(self):
        c = Conclusion(
            statement="Risk is high",
            conclusion_type=ConclusionType.INFERRED,
            reasoning_path="Aggregate of forecast and twin state",
        )
        assert c.conclusion_type == ConclusionType.INFERRED
        assert c.reasoning_path is not None


class TestAssumption:
    def test_create_assumption(self):
        a = Assumption(
            statement="Data is from 2024",
            confidence=0.7,
            reasoning="Based on metadata timestamp",
        )
        assert a.statement == "Data is from 2024"
        assert a.confidence == 0.7


class TestUnknown:
    def test_create_unknown(self):
        u = Unknown(
            question="What is the sea level rise?",
            reason="No data available for this metric",
            suggested_sources=["NASA", "IPCC"],
        )
        assert u.question == "What is the sea level rise?"
        assert len(u.suggested_sources) == 2


class TestReasoningOutput:
    def test_empty_output(self):
        output = ReasoningOutput()
        assert not output.has_conclusions
        assert not output.has_unknowns
        assert output.strategy == ReasoningStrategy.RULE_BASED

    def test_with_conclusions(self):
        output = ReasoningOutput(
            conclusions=[
                Conclusion(statement="C1", confidence=0.9),
                Conclusion(statement="C2", confidence=0.8),
            ],
            strategy=ReasoningStrategy.GRAPH_BASED,
        )
        assert output.has_conclusions
        assert output.strategy == ReasoningStrategy.GRAPH_BASED
        assert len(output.get_statements()) == 2

    def test_with_unknowns(self):
        output = ReasoningOutput(
            unknowns=[Unknown(question="Q1", reason="No data")],
        )
        assert output.has_unknowns

    def test_reasoning_trace(self):
        output = ReasoningOutput(
            reasoning_trace=[
                "Step 1: Rule matching",
                "Step 2: Evidence grouping",
                "Step 3: Conclusion generation",
            ],
        )
        assert len(output.reasoning_trace) == 3

    def test_confidence_calculation(self):
        output = ReasoningOutput(
            conclusions=[
                Conclusion(statement="C1", confidence=0.9),
                Conclusion(statement="C2", confidence=0.7),
            ],
            confidence=0.8,
        )
        assert output.confidence == 0.8
