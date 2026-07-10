"""Grounding models for the Grounding Stage.

Maps claims to evidence, detects unsupported claims,
and computes grounding confidence per statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClaimVerification:
    """Verification result for a single claim."""

    claim: str
    supported: bool = False
    confidence: float = 0.0
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradictory_evidence_ids: list[str] = field(default_factory=list)
    missing_evidence_reason: str | None = None


@dataclass
class UnsupportedClaim:
    """A claim that could not be grounded in evidence."""

    claim: str
    reason: str
    severity: str = "warning"  # "warning", "error"
    suggested_action: str | None = None


@dataclass
class GroundingReport:
    """Complete grounding report for a set of claims.

    Produced by the Grounding Stage.
    Maps every claim to its supporting/contradicting evidence.
    """

    claim_verifications: list[ClaimVerification] = field(default_factory=list)
    unsupported_claims: list[UnsupportedClaim] = field(default_factory=list)
    overall_grounding_confidence: float = 1.0
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_count: int = 0

    @property
    def passed(self) -> bool:
        """Grounding passes if confidence > 0.5 and no critical unsupported claims."""
        if self.overall_grounding_confidence < 0.3:
            return False
        critical = [uc for uc in self.unsupported_claims if uc.severity == "error"]
        return len(critical) == 0

    @property
    def grounding_score(self) -> float:
        """Fraction of claims that are supported."""
        if self.total_claims == 0:
            return 1.0
        return self.supported_claims / self.total_claims
