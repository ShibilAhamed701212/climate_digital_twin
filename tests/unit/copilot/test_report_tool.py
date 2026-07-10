"""Unit tests for ReportGeneratorTool."""

from unittest.mock import patch

from requests.exceptions import ConnectionError, HTTPError, Timeout

from copilot.tools.report_tool import ReportGeneratorTool, _synthetic_report


class TestSyntheticReport:
    def test_synthetic_report_format(self):
        result = _synthetic_report("Karnataka", "summary")
        assert "Karnataka" in result
        assert "summary" in result
        assert "32.5" in result
        assert "Climate Copilot" in result


class TestReportGeneratorTool:
    def setup_method(self):
        self.tool = ReportGeneratorTool()

    def test_run_success(self):
        with patch.object(self.tool._client, "generate_report", return_value="# Real Report"):
            result = self.tool.run(location="Karnataka", report_type="summary")
            assert result["report"] == "# Real Report"
            assert result["fallback"] is False

    def test_run_connection_error(self):
        with patch.object(
            self.tool._client, "generate_report", side_effect=ConnectionError("refused")
        ):
            result = self.tool.run(location="Karnataka")
            assert result["fallback"] is True
            assert "Climate Report" in result["report"]

    def test_run_timeout(self):
        with patch.object(self.tool._client, "generate_report", side_effect=Timeout("timed out")):
            result = self.tool.run(location="Mysuru", report_type="detailed")
            assert result["fallback"] is True
            assert result["location"] == "Mysuru"

    def test_run_http_error(self):
        with patch.object(self.tool._client, "generate_report", side_effect=HTTPError("500 error")):
            result = self.tool.run(location="Karnataka")
            assert result["fallback"] is True

    def test_validate_invalid_type(self):
        valid, msg = self.tool.validate(report_type="invalid")
        assert valid is False
        assert "report_type" in msg

    def test_validate_invalid_location(self):
        valid, msg = self.tool.validate(location=123)
        assert valid is False
        assert "location" in msg

    def test_validate_valid(self):
        valid, msg = self.tool.validate(location="Karnataka", report_type="summary")
        assert valid is True
        assert msg == ""

    def test_describe(self):
        desc = self.tool.describe()
        assert desc["name"] == "report_generator"
        assert "parameters" in desc

    def test_health_check(self):
        ok, msg = self.tool.health_check()
        assert ok is True
