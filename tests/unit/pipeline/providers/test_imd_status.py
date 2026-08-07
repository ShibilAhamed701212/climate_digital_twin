"""Unit tests for pipeline/providers/imd_status.py."""

from __future__ import annotations

from pipeline.providers.fetch_result import AUTH_REQUIRED
from pipeline.providers.imd_status import fetch_imd


def test_fetch_imd():
    res = fetch_imd(12.97, 77.59)
    assert res.status == "FAILED"
    assert res.error_code == AUTH_REQUIRED
    assert res.request_metadata["latitude"] == 12.97
