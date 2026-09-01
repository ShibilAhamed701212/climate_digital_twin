from __future__ import annotations

from pathlib import Path

from dashboard.config.config import PAGES


def test_page_11_registered() -> None:
    files = {p["file"] for p in PAGES}
    assert "11_disaster_intelligence" in files


def test_page_11_shows_model_provenance_not_fake_accuracy() -> None:
    text = Path("dashboard/page_views/11_disaster_intelligence.py").read_text(encoding="utf-8")
    assert "softmax_margin" in text or "Softmax margin" in text
    assert "not a calibrated flood probability" in text
    assert "Processing status" in text
    assert "Flood model" in text
