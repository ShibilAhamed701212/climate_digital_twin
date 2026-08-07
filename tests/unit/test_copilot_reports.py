"""Unit tests for conversation reports."""

import json
import os
import tempfile

from copilot.memory.conversation_memory import ConversationMemory
from copilot.models import ConversationTurn, IntentType, Plan, ToolResult
from copilot.reports.conversation_report import ConversationReport


def _make_turn(query: str, response: str) -> ConversationTurn:
    return ConversationTurn(
        query=query,
        intent=IntentType.FORECAST,
        plan=Plan(intent=IntentType.FORECAST, steps=[], required_context=[]),
        results=[
            ToolResult(
                tool_name="forecast_tool", success=True, data={"key": "val"}, execution_time_ms=10.0
            )
        ],
        response=response,
        latency_ms=15.0,
        citations=["Source: Test"],
    )


class TestConversationReport:
    def setup_method(self):
        self.memory = ConversationMemory(window_size=10, expiration_minutes=60)

    def test_generate_summary(self):
        cid = self.memory.create_conversation()
        self.memory.add_turn(cid, _make_turn("weather?", "sunny"))
        report = ConversationReport(self.memory)
        summary = report.generate_summary(cid)
        assert summary["total_turns"] == 1
        assert summary["conversation_id"] == cid

    def test_generate_markdown(self):
        cid = self.memory.create_conversation()
        self.memory.add_turn(cid, _make_turn("weather?", "sunny"))
        report = ConversationReport(self.memory)
        md = report.generate_markdown(cid)
        assert "Conversation Report" in md
        assert "weather?" in md
        assert "sunny" in md

    def test_save_json_report(self):
        cid = self.memory.create_conversation()
        self.memory.add_turn(cid, _make_turn("q", "a"))
        with tempfile.TemporaryDirectory() as tmp:
            report = ConversationReport(self.memory, output_dir=tmp)
            saved = report.save_report(cid, formats=["json"])
            assert "json" in saved
            assert os.path.exists(saved["json"])
            with open(saved["json"], encoding="utf-8") as f:
                data = json.load(f)
            assert data["conversation_id"] == cid

    def test_save_markdown_report(self):
        cid = self.memory.create_conversation()
        self.memory.add_turn(cid, _make_turn("q", "a"))
        with tempfile.TemporaryDirectory() as tmp:
            report = ConversationReport(self.memory, output_dir=tmp)
            saved = report.save_report(cid, formats=["markdown"])
            assert "markdown" in saved
            assert os.path.exists(saved["markdown"])

    def test_empty_conversation_summary(self):
        cid = self.memory.create_conversation()
        report = ConversationReport(self.memory)
        summary = report.generate_summary(cid)
        assert summary["total_turns"] == 0
