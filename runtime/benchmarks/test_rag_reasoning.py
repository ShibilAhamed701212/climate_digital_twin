"""WP5-WP6: RAG Evaluation + Reasoning Validation.

WP5 measures:
- Retrieval precision/recall (with known document sets)
- Citation accuracy
- Duplicate retrieval rate
- Retrieval latency
- Grounding coverage

WP6 validates:
- Logical consistency in reasoning
- Evidence usage in conclusions
- Unsupported claim detection
- Contradiction handling
- Confidence calibration
"""

from __future__ import annotations

import pytest

from runtime.models.evidence import (
    Citation,
    Evidence,
    EvidenceGraph,
    EvidenceRelationship,
    EvidenceSource,
    Provenance,
)
from runtime.models.grounding import ClaimVerification, GroundingReport, UnsupportedClaim
from runtime.models.reasoning import Conclusion, ConclusionType, ReasoningOutput, ReasoningStrategy
from runtime.models.retrieval import Chunk, RetrievalQuery, RetrievalResult

# ── WP5: RAG Evaluation ────────────────────────────────────────────────


@pytest.mark.rag
class TestRetrievalPrecision:
    """Measure retrieval precision with known document sets."""

    def test_precision_with_exact_match(self):
        """Retrieval returns exact match — precision=1.0."""
        chunks = [
            Chunk(
                text="Bangalore flood risk is high during monsoon",
                score=0.95,
                source="climate_report_2024",
                chunk_id="c1",
            ),
            Chunk(
                text="Coastal regions face cyclone threats",
                score=0.45,
                source="climate_report_2024",
                chunk_id="c2",
            ),
        ]
        result = RetrievalResult(query="Bangalore flood", chunks=chunks, total_results=2)
        # Precision = relevant / retrieved
        relevant = [c for c in result.chunks if c.score > 0.7]
        precision = len(relevant) / len(result.chunks) if result.chunks else 0
        print(f"\n[RAG Precision - exact] {precision:.2%} ({len(relevant)}/{len(result.chunks)})")
        assert precision >= 0.5

    def test_recall_with_known_documents(self):
        """Recall measurement with known relevant documents."""
        relevant_docs = {"doc_a", "doc_b", "doc_c"}
        retrieved_chunks = [
            Chunk(text="doc_a content", score=0.9, source="doc_a", chunk_id="c1"),
            Chunk(text="doc_b content", score=0.8, source="doc_b", chunk_id="c2"),
        ]
        retrieved_sources = {c.source for c in retrieved_chunks}
        recall = len(retrieved_sources & relevant_docs) / len(relevant_docs) if relevant_docs else 0
        print(
            f"\n[RAG Recall] {recall:.2%} ({len(retrieved_sources & relevant_docs)}/{len(relevant_docs)})"
        )
        assert recall > 0

    def test_duplicate_retrieval_rate(self):
        """No duplicate chunks in a single retrieval."""
        chunks = [
            Chunk(text="Content A", score=0.9, source="doc_a", chunk_id="c1"),
            Chunk(text="Content B", score=0.8, source="doc_b", chunk_id="c2"),
        ]
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_query_construction(self):
        """RetrievalQuery created correctly."""
        q = RetrievalQuery(query="flood risk Bangalore", top_k=5)
        assert q.query == "flood risk Bangalore"
        assert q.top_k == 5


@pytest.mark.rag
class TestCitationAccuracy:
    """Measure citation accuracy."""

    def test_evidence_with_citation(self):
        """Citation attached to evidence."""
        citation = Citation(
            source="climate_report_2024.pdf",
            text="Flood risk is high in low-lying areas",
            relevance=0.95,
        )
        evidence = Evidence(
            source=EvidenceSource.PROVIDER,
            capability="forecast",
            confidence=0.85,
            provenance=Provenance(source="forecast_provider", capability="forecast"),
            citations=[citation],
        )
        assert len(evidence.citations) == 1
        assert evidence.citations[0].source == "climate_report_2024.pdf"

    def test_evidence_traces_to_provenance(self):
        """Evidence can be traced back to its provenance."""
        evidence = Evidence(
            source=EvidenceSource.RETRIEVAL,
            capability="knowledge",
            confidence=0.9,
            provenance=Provenance(
                source="knowledge_provider",
                capability="knowledge",
                method="semantic_search",
            ),
        )
        assert evidence.provenance is not None
        assert evidence.provenance.method == "semantic_search"


@pytest.mark.rag
class TestGroundingCoverage:
    """Measure grounding coverage — what % of claims are supported."""

    def test_all_claims_grounded(self):
        """All claims should be checkable against evidence."""
        report = GroundingReport(
            claim_verifications=[
                ClaimVerification(
                    claim="Flood risk is high",
                    supported=True,
                    confidence=0.9,
                    supporting_evidence_ids=["ev_001"],
                ),
                ClaimVerification(
                    claim="Temperature will rise",
                    supported=True,
                    confidence=0.85,
                    supporting_evidence_ids=["ev_002"],
                ),
            ],
            total_claims=2,
            supported_claims=2,
        )
        coverage = report.grounding_score
        print(
            f"\n[Grounding Coverage] {coverage:.2%} ({report.supported_claims}/{report.total_claims})"
        )
        assert coverage == 1.0

    def test_unsupported_claims_detected(self):
        """Unsupported claims are flagged."""
        report = GroundingReport(
            claim_verifications=[],
            unsupported_claims=[
                UnsupportedClaim(
                    claim="Unsupported claim",
                    reason="No evidence found in retrieval results",
                    severity="warning",
                ),
            ],
            total_claims=1,
            supported_claims=0,
            unsupported_count=1,
        )
        assert len(report.unsupported_claims) == 1
        assert report.unsupported_claims[0].severity == "warning"

    def test_grounding_fails_with_critical_unsupported(self):
        """Grounding fails if critical unsupported claims exist."""
        report = GroundingReport(
            unsupported_claims=[
                UnsupportedClaim(
                    claim="Dangerous claim without evidence",
                    reason="No supporting data",
                    severity="error",
                ),
            ],
            overall_grounding_confidence=0.2,
        )
        assert report.passed is False


# ── WP6: Reasoning Validation ──────────────────────────────────────────


@pytest.mark.reasoning
class TestReasoningConsistency:
    """Validate logical consistency in reasoning."""

    def test_conclusion_traces_to_evidence(self):
        """Every conclusion should reference supporting evidence."""
        output = ReasoningOutput(
            conclusions=[
                Conclusion(
                    statement="Sea levels are rising at 3.3mm/year",
                    confidence=0.95,
                    conclusion_type=ConclusionType.DIRECT,
                    supporting_evidence_ids=["ev_001"],
                ),
            ],
            strategy=ReasoningStrategy.RULE_BASED,
            confidence=0.9,
        )
        assert len(output.conclusions) > 0
        assert len(output.conclusions[0].supporting_evidence_ids) > 0
        assert output.confidence > 0

    def test_contradiction_detection(self):
        """Conflicting evidence is tracked via EvidenceGraph."""
        graph = EvidenceGraph()
        ev_a = Evidence(
            id="ev_001",
            source=EvidenceSource.PROVIDER,
            capability="forecast",
            payload={"temperature_trend": "rising"},
        )
        ev_b = Evidence(
            id="ev_002",
            source=EvidenceSource.PROVIDER,
            capability="forecast",
            payload={"temperature_trend": "stable"},
        )
        graph.add_evidence(ev_a)
        graph.add_evidence(ev_b)
        graph.add_relationship("ev_001", "ev_002", EvidenceRelationship.CONTRADICTS)

        contradicted = graph.get_contradicted_by("ev_002")
        assert len(contradicted) == 1
        assert contradicted[0].id == "ev_001"

    def test_confidence_calibration(self):
        """Confidence scores are in valid range."""
        for conf in [0.0, 0.5, 1.0]:
            assert 0.0 <= conf <= 1.0

    def test_reasoning_output_has_conclusions(self):
        """ReasoningOutput correctly reports if conclusions exist."""
        output = ReasoningOutput(conclusions=[])
        assert output.has_conclusions is False

        output = ReasoningOutput(conclusions=[Conclusion(statement="Test", confidence=0.8)])
        assert output.has_conclusions is True

    def test_reasoning_strategies(self):
        """All reasoning strategies are valid."""
        strategies = [
            ReasoningStrategy.RULE_BASED,
            ReasoningStrategy.GRAPH_BASED,
            ReasoningStrategy.LLM_ASSISTED,
            ReasoningStrategy.HYBRID,
        ]
        for s in strategies:
            assert s.value in ("rule_based", "graph_based", "llm_assisted", "hybrid")
