"""Tests for dashboard/pages/09_feedback.py — render() function."""

from __future__ import annotations


def test_feedback_render_does_not_crash():
    m = __import__("dashboard.page_views.09_feedback", fromlist=["render"])

    m.render(None, {})
    assert True


def test_feedback_render_with_filters():
    m = __import__("dashboard.page_views.09_feedback", fromlist=["render"])

    m.render(None, {"location_id": "KA-BLR-001", "variable": "Rainfall"})
    assert True
