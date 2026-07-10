"""Tests for provider executor."""

import asyncio

import pytest

from runtime.models.provider import ProviderRequest, ProviderResult
from runtime.models.runtime import RuntimeContext
from runtime.providers.executor import run_provider_safely


@pytest.mark.asyncio
class TestRunProviderSafely:
    async def test_async_provider(self):
        async def async_exec(_req):
            await asyncio.sleep(0.01)
            return ProviderResult(success=True, data={"value": 42})

        result = await run_provider_safely(
            async_exec,
            ProviderRequest(capability="test", params={}, context=RuntimeContext()),
            provider_id="test_provider",
        )
        assert result.success
        assert result.data["value"] == 42

    async def test_sync_provider(self):
        def sync_exec(_req):
            return ProviderResult(success=True, data={"value": "sync"})

        result = await run_provider_safely(
            sync_exec,
            ProviderRequest(capability="test", params={}, context=RuntimeContext()),
            provider_id="sync_provider",
        )
        assert result.success
        assert result.data["value"] == "sync"

    async def test_timeout(self):
        async def slow_exec(_req):
            await asyncio.sleep(10)
            return ProviderResult(success=True, data={})

        result = await run_provider_safely(
            slow_exec,
            ProviderRequest(capability="test", params={}, context=RuntimeContext()),
            timeout_ms=50,
            provider_id="slow",
        )
        assert not result.success
        assert "timed out" in result.error

    async def test_exception(self):
        def failing_exec(_req):
            raise ValueError("provider error")

        result = await run_provider_safely(
            failing_exec,
            ProviderRequest(capability="test", params={}, context=RuntimeContext()),
            provider_id="failing",
        )
        assert not result.success
        assert "provider error" in result.error

    async def test_dict_return(self):
        def dict_exec(_req):
            return {"result": "direct dict"}

        result = await run_provider_safely(
            dict_exec,
            ProviderRequest(capability="test", params={}, context=RuntimeContext()),
            provider_id="dict_return",
        )
        assert result.success
        assert result.data["result"] == "direct dict"
