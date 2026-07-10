"""GroundingStage — maps claims to evidence, detects unsupported claims.

Runtime-native stage. Domain-agnostic.
Generic claim verification — no domain-specific knowledge.

Responsibilities:
- Extract claims from the pipeline context
- Map each claim to supporting Evidence
- Detect unsupported claims (no evidence, low confidence)
- Detect contradictory evidence
- Compute overall grounding confidence
- Produce GroundingReport
"""

from __future__ import annotations

import re

from runtime.events.definitions import (
    GROUNDING_COMPLETED,
    GROUNDING_STARTED,
    GROUNDING_UNSUPPORTED_DETECTED,
)
from runtime.models.events import Event as RuntimeEvent
from runtime.models.evidence import Evidence, EvidenceGraph
from runtime.models.grounding import (
    ClaimVerification,
    GroundingReport,
    UnsupportedClaim,
)
from runtime.models.pipeline import ExecutionContext, PipelineStage


class GroundingStage(PipelineStage):
    """Verify that all claims in the response are grounded in evidence.

    Reads: blackboard "evidence.list", "evidence.graph"
           stage_outputs (for any response context)
    Writes: blackboard keys under "grounding.*"
            stage_outputs["grounding"] = GroundingReport

    This is a mandatory gate — unsupported claims must not reach the user.
    """

    name = "grounding"
    description = "Map claims to evidence, detect unsupported claims"

    def __init__(self, min_confidence: float = 0.3) -> None:
        super().__init__()
        self._min_confidence = min_confidence

    async def execute(self, ctx: ExecutionContext) -> ExecutionContext:
        ctx.event_bus.publish(
            RuntimeEvent(
                type=GROUNDING_STARTED,
                data={"stage": self.name},
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        # Get evidence and graph from blackboard
        evidence_list: list[Evidence] = []
        evidence_entry = ctx.blackboard.get("evidence.list")
        if evidence_entry and isinstance(evidence_entry.value, list):
            evidence_list = evidence_entry.value

        graph_entry = ctx.blackboard.get("evidence.graph")
        graph: EvidenceGraph | None = graph_entry.value if graph_entry else None

        # Extract claims to verify
        claims = self._extract_claims(ctx)

        claim_verifications: list[ClaimVerification] = []
        unsupported_claims: list[UnsupportedClaim] = []
        supported_count = 0

        for claim in claims:
            verification = self._verify_claim(claim, evidence_list, graph)
            claim_verifications.append(verification)

            if verification.supported:
                supported_count += 1
            elif (
                not verification.supported
                and verification.confidence < self._min_confidence
            ):
                unsupported_claims.append(
                    UnsupportedClaim(
                        claim=claim,
                        reason=(
                            verification.missing_evidence_reason
                            or "No sufficient evidence found"
                        ),
                        severity="error"
                        if verification.confidence < 0.2
                        else "warning",
                    )
                )

        total = len(claims)
        unsupported_count = len(unsupported_claims)
        grounding_score = float(supported_count / total) if total > 0 else 1.0

        report = GroundingReport(
            claim_verifications=claim_verifications,
            unsupported_claims=unsupported_claims,
            overall_grounding_confidence=grounding_score,
            total_claims=total,
            supported_claims=supported_count,
            unsupported_count=unsupported_count,
        )

        ctx.blackboard.publish("grounding.report", report, self.name)
        ctx.blackboard.publish(
            "grounding.claim_verifications", claim_verifications, self.name
        )
        ctx.blackboard.publish(
            "grounding.unsupported_claims", unsupported_claims, self.name
        )
        ctx.blackboard.publish("grounding.confidence", grounding_score, self.name)
        ctx.blackboard.publish("grounding.passed", report.passed, self.name)
        ctx.stage_outputs["grounding"] = report

        ctx.add_metric("grounding.total_claims", total)
        ctx.add_metric("grounding.supported", supported_count)
        ctx.add_metric("grounding.unsupported", unsupported_count)
        ctx.add_metric("grounding.confidence", grounding_score)

        if unsupported_claims:
            ctx.event_bus.publish(
                RuntimeEvent(
                    type=GROUNDING_UNSUPPORTED_DETECTED,
                    data={
                        "count": len(unsupported_claims),
                        "claims": [uc.claim[:100] for uc in unsupported_claims],
                    },
                    source=self.name,
                    trace_id=ctx.runtime_context.trace_id,
                )
            )

        ctx.event_bus.publish(
            RuntimeEvent(
                type=GROUNDING_COMPLETED,
                data={
                    "total_claims": total,
                    "supported": supported_count,
                    "unsupported": unsupported_count,
                    "confidence": grounding_score,
                    "passed": report.passed,
                },
                source=self.name,
                trace_id=ctx.runtime_context.trace_id,
            )
        )

        return ctx

    def _extract_claims(self, ctx: ExecutionContext) -> list[str]:
        """Extract claims to verify from pipeline context."""
        claims: list[str] = []

        # Extract from reasoning output if available
        reasoning = ctx.stage_outputs.get("reasoning")
        if reasoning and hasattr(reasoning, "conclusions"):
            for c in reasoning.conclusions:
                if hasattr(c, "statement") and c.statement:
                    claims.append(c.statement)

        # Extract from response draft if available
        response = ctx.stage_outputs.get("response", "")
        if response:
            # Split into sentences as potential claims
            sentences = re.split(r"[.!?]+", response)
            for s in sentences:
                s = s.strip()
                if s and len(s) > 20:
                    claims.append(s)

        # Extract from provider results for pre-response verification
        if not claims:
            provider_results = ctx.stage_outputs.get("provider_results")
            if provider_results and hasattr(provider_results, "items"):
                for item in provider_results.items:
                    if hasattr(item, "data") and item.data:
                        for key, value in item.data.items():
                            if isinstance(value, (str, int, float)):
                                claims.append(f"{key}: {value}")
                            elif isinstance(value, dict):
                                for k, v in value.items():
                                    if isinstance(v, (str, int, float)):
                                        claims.append(f"{k}: {v}")

        return claims

    def _verify_claim(
        self,
        claim: str,
        evidence_list: list[Evidence],
        graph: EvidenceGraph | None,
    ) -> ClaimVerification:
        """Verify a single claim against available evidence."""
        claim_lower = claim.lower()
        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []
        best_confidence = 0.0

        for ev in evidence_list:
            # Check for keyword overlap between claim and evidence payload
            match_score = self._compute_match(claim_lower, ev)
            if match_score > 0.5:
                supporting_ids.append(ev.id)
                best_confidence = max(best_confidence, ev.confidence * match_score)

            # Check for contradictions
            if graph:
                contradicted_by = graph.get_contradicted_by(ev.id)
                if contradicted_by:
                    contradicting_ids.append(ev.id)

        supported = best_confidence >= self._min_confidence or len(supporting_ids) > 0
        missing_reason = None

        if not supported:
            if not evidence_list:
                missing_reason = "No evidence available"
            elif best_confidence < self._min_confidence:
                missing_reason = (
                    f"Insufficient evidence confidence ({best_confidence:.2f})"
                )
            else:
                missing_reason = "No matching evidence found"

        return ClaimVerification(
            claim=claim,
            supported=supported,
            confidence=best_confidence,
            supporting_evidence_ids=supporting_ids,
            contradictory_evidence_ids=contradicting_ids,
            missing_evidence_reason=missing_reason,
        )

    def _compute_match(self, claim: str, evidence: Evidence) -> float:
        """Compute a simple keyword overlap between claim and evidence payload."""
        evidence_text = str(evidence.payload)
        evidence_lower = evidence_text.lower()

        # Extract key terms from claim (words longer than 3 chars)
        terms = [
            w.strip(".,!?;:'\"()[]{}")
            for w in claim.split()
            if len(w.strip(".,!?;:'\"()[]{}")) > 3
        ]

        if not terms:
            return 0.0

        matches = sum(1 for t in terms if t in evidence_lower)
        return matches / len(terms)
