from __future__ import annotations

from backend.api.rate_limit import reset_memory_limiter, take_token


def test_memory_limiter_allows_then_blocks(monkeypatch) -> None:
    monkeypatch.delenv("RATE_LIMIT_REDIS_URL", raising=False)
    reset_memory_limiter()
    allowed, _, remaining = take_token("ip:test", limit=2, window_s=60)
    assert allowed is True
    assert remaining == 1
    allowed, _, remaining = take_token("ip:test", limit=2, window_s=60)
    assert allowed is True
    assert remaining == 0
    allowed, retry, remaining = take_token("ip:test", limit=2, window_s=60)
    assert allowed is False
    assert retry >= 1
    assert remaining == 0


def test_redis_down_falls_back_to_memory(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_REDIS_URL", "redis://127.0.0.1:1")
    reset_memory_limiter()
    allowed, _, _ = take_token("ip:fallback", limit=1, window_s=60)
    assert allowed is True
    allowed, _, _ = take_token("ip:fallback", limit=1, window_s=60)
    assert allowed is False
