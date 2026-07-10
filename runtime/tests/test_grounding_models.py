"""Tests for Grounding models."""


from runtime.models.grounding import (
    ClaimVerification,
    GroundingReport,
    UnsupportedClaim,
)


class TestClaimVerification:
    def test_supported_claim(self):
        cv = ClaimVerification(
            claim="Temperature is 32C",
            supported=True,
            confidence=0.9,
            supporting_evidence_ids=["ev_001"],
        )
        assert cv.supported
        assert cv.confidence == 0.9
        assert len(cv.supporting_evidence_ids) == 1

    def test_unsupported_claim(self):
        cv = ClaimVerification(
            claim="Unknown fact",
            supported=False,
            confidence=0.0,
            missing_evidence_reason="No evidence found",
        )
        assert not cv.supported
        assert cv.missing_evidence_reason == "No evidence found"


class TestUnsupportedClaim:
    def test_warning_severity(self):
        uc = UnsupportedClaim(
            claim="Temperature will be 100C",
            reason="Contradicts all evidence",
            severity="warning",
        )
        assert uc.severity == "warning"

    def test_error_severity(self):
        uc = UnsupportedClaim(
            claim="Bangalore is coastal",
            reason="No geographic support",
            severity="error",
            suggested_action="Verify location data",
        )
        assert uc.severity == "error"
        assert uc.suggested_action == "Verify location data"


class TestGroundingReport:
    def test_empty_report(self):
        report = GroundingReport()
        assert report.passed
        assert report.grounding_score == 1.0

    def test_full_support(self):
        report = GroundingReport(
            claim_verifications=[
                ClaimVerification(claim="C1", supported=True, confidence=0.9),
                ClaimVerification(claim="C2", supported=True, confidence=0.95),
            ],
            total_claims=2,
            supported_claims=2,
            overall_grounding_confidence=0.9,
        )
        assert report.passed
        assert report.grounding_score == 1.0

    def test_unsupported_error(self):
        report = GroundingReport(
            claim_verifications=[
                ClaimVerification(claim="C1", supported=False, confidence=0.0),
            ],
            unsupported_claims=[
                UnsupportedClaim(claim="C1", reason="No evidence", severity="error"),
            ],
            total_claims=1,
            unsupported_count=1,
            overall_grounding_confidence=0.0,
        )
        assert not report.passed
        assert report.grounding_score == 0.0

    def test_unsupported_warning(self):
        """Warning-level unsupported claims should still pass grounding."""
        report = GroundingReport(
            claim_verifications=[
                ClaimVerification(claim="C1", supported=True, confidence=0.9),
            ],
            unsupported_claims=[
                UnsupportedClaim(
                    claim="Minor assumption",
                    reason="Low confidence",
                    severity="warning",
                ),
            ],
            total_claims=2,
            supported_claims=1,
            unsupported_count=1,
            overall_grounding_confidence=0.7,
        )
        # Warning-level should pass as long as overall confidence > 0.3
        assert report.passed
