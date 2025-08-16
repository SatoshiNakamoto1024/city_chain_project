# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_middleware.py
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from poh_metrics.middleware import metrics_middleware
from poh_metrics.metrics import register_metrics
from prometheus_client import CollectorRegistry


@pytest.mark.asyncio
async def test_http_middleware(monkeypatch):
    # 固定 Registry を使わせる
    reg = CollectorRegistry()
    register_metrics(reg)
    monkeypatch.setattr("poh_metrics.registry.get_registry", lambda: reg)

    called = {}

    async def fake_observe(result: str, latency: float, registry=None):
        called["result"] = result
        called["latency"] = latency

    monkeypatch.setattr("poh_metrics.middleware.observe_verify", fake_observe)

    async def handler(request):
        return web.Response(text="OK", status=201)

    app = web.Application(middlewares=[metrics_middleware])
    app.router.add_get("/", handler)

    async with TestClient(TestServer(app)) as client:
        resp = await client.get("/")
        assert resp.status == 201

    # fake_observe が呼ばれた
    assert called["result"] in ("success", "failure")
    assert isinstance(called["latency"], float)
