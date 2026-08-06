"""Unit tests for risk report generation."""

import json
import os
import tempfile

import pytest


class TestReportGenerator:
    """Test report generation in JSON and Markdown formats."""

    @pytest.fixture
    def sample_report(self):
        from risk.models.risk_models import (
            ClimateInsight,
            CompositeRiskScore,
            DroughtRiskScore,
            FeatureAttribution,
            FloodRiskScore,
            HeatRiskScore,
            RiskReport,
            SHAPExplanation,
        )

        return RiskReport(
            location_id="KA-BLR-001",
            district="Bangalore",
            heat_risk=HeatRiskScore(45.0, 30.0, 10.0, 5.0, 5, 2.3),
            flood_risk=FloodRiskScore(30.0, 15.0, 10.0, 5.0, 120.0, 80.0),
            drought_risk=DroughtRiskScore(20.0, 10.0, 5.0, 5.0, -15.0, 1.5),
            composite_risk=CompositeRiskScore(
                33.0, 45.0, 30.0, 20.0, {"heat": 0.33, "flood": 0.33, "drought": 0.34}
            ),
            explanation=SHAPExplanation(
                prediction=33.0,
                base_value=50.0,
                feature_attributions=[
                    FeatureAttribution("max_temp", 2.0, 35.0, "positive"),
                    FeatureAttribution("rainfall", -1.5, 80.0, "negative"),
                ],
                top_features=["max_temp", "rainfall"],
                positive_contributors=[FeatureAttribution("max_temp", 2.0, 35.0, "positive")],
                negative_contributors=[FeatureAttribution("rainfall", -1.5, 80.0, "negative")],
                confidence=0.85,
                risk_interpretation="Moderate risk with temperature as primary driver.",
            ),
            insights=[
                ClimateInsight(
                    "max_temp", "increasing", 2.3, "Temp above average.", "Heat stress risk."
                ),
            ],
        )

    def test_generate_json_report(self, sample_report):
        from risk.reports.report_generator import generate_report

        output_dir = tempfile.mkdtemp()
        result = generate_report(
            "KA-BLR-001", "Bangalore", sample_report, output_dir=output_dir, formats=["json"]
        )
        assert "json" in result
        json_path = result["json"]
        assert os.path.exists(json_path)
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["location_id"] == "KA-BLR-001"
        assert data["district"] == "Bangalore"
        assert "composite_risk" in data
        assert "heat_risk" in data
        assert "explanation" in data

    def test_generate_markdown_report(self, sample_report):
        from risk.reports.report_generator import generate_report

        output_dir = tempfile.mkdtemp()
        result = generate_report(
            "KA-BLR-001", "Bangalore", sample_report, output_dir=output_dir, formats=["markdown"]
        )
        assert "markdown" in result
        md_path = result["markdown"]
        assert os.path.exists(md_path)
        with open(md_path, encoding="utf-8") as f:
            content = f.read()
        assert "# Climate Risk Report" in content
        assert "KA-BLR-001" in content
        assert "Bangalore" in content
        assert "Composite Climate Risk Index" in content
        assert "Heat Risk" in content
        assert "Heavy Rain Risk" in content
        assert "Dryness Risk" in content
        assert "AI Explanation (SHAP)" in content
        assert "Climate Insights" in content

    def test_generate_both_formats(self, sample_report):
        from risk.reports.report_generator import generate_report

        output_dir = tempfile.mkdtemp()
        result = generate_report(
            "KA-BLR-001",
            "Bangalore",
            sample_report,
            output_dir=output_dir,
            formats=["json", "markdown"],
        )
        assert "json" in result
        assert "markdown" in result

    def test_report_directory_created(self, sample_report):
        from risk.reports.report_generator import generate_report

        output_dir = os.path.join(tempfile.mkdtemp(), "nested", "outputs")
        result = generate_report(
            "KA-BLR-001", "Bangalore", sample_report, output_dir=output_dir, formats=["json"]
        )
        assert os.path.exists(os.path.dirname(result["json"]))

    def test_minimal_report_fields(self):
        from risk.models.risk_models import RiskReport
        from risk.reports.report_generator import generate_report

        report = RiskReport(location_id="KA-BLR-001", district="Bangalore")
        output_dir = tempfile.mkdtemp()
        result = generate_report(
            "KA-BLR-001", "Bangalore", report, output_dir=output_dir, formats=["json"]
        )
        with open(result["json"], encoding="utf-8") as f:
            data = json.load(f)
        assert data["composite_risk"] is None
        assert data["explanation"] is None
