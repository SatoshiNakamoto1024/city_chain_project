# D:\city_chain_project\network\DAGs\common\observability\test_observability.py
"""
test_observability.py
---------------------
Observability サブシステムの E2E テスト

* OpenTelemetry tracer が span を生成しているか
* Prometheus metrics が増えるか

外部 OTLP Collector / Prometheus Server は使わず
インメモリ Exporter と prometheus_client.generate_latest で検証。
"""
from __future__ import annotations
import asyncio
import inspect
import pytest
import httpx
from prometheus_client import generate_latest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry import trace
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.app_observability import app

# ────────────────────────────────
# 1. OpenTelemetry を InMemory Exporter に差替え
# ────────────────────────────────
_exporter = InMemorySpanExporter()
tracer_provider = trace.get_tracer_provider()
# 既に付いている OTLP exporter は残しても支障ない
tracer_provider.add_span_processor(SimpleSpanProcessor(_exporter))


# ────────────────────────────────
# 2. httpx バージョン互換クライアント
# ────────────────────────────────
def get_client() -> httpx.AsyncClient:
    if "app" in inspect.signature(httpx.AsyncClient.__init__).parameters:
        return httpx.AsyncClient(app=app, base_url="http://t")
    trans_sig = inspect.signature(httpx.ASGITransport.__init__)
    tr = httpx.ASGITransport(app=app, lifespan="off") if "lifespan" in trans_sig.parameters \
        else httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=tr, base_url="http://t")


# ────────────────────────────────
# 3. テスト本体
# ────────────────────────────────
@pytest.mark.asyncio
async def test_observability_metrics_and_tracing():
    async with get_client() as cli:
        # 3 回 /ping, 2 回 /poh
        for _ in range(3):
            assert (await cli.get("/ping")).status_code == 200
        for _ in range(2):
            assert (await cli.post("/poh")).status_code == 200

    # ---------- ① Span が 5 個生成されているか ----------
    spans = _exporter.get_finished_spans()
    # ① 最低 5 個以上生成されていること
    assert len(spans) >= 5
    # ② ルート span（/ping, /poh）が含まれること
    root_names = {s.name for s in spans if s.parent is None}
    assert "/ping" in root_names and "/poh" in root_names

    # ---------- ② Prometheus Metrics が増えているか ----------
    metrics_text = generate_latest().decode()
    # /ping 分
    assert 'poh_requests_total{endpoint="/ping",status="200"} 3.0' in metrics_text
    # /poh 分（REQUEST + ACK）
    # Middleware とエンドポイントの両方が加算 → 少なくとも 2 以上
    import re
    m = re.search(r'poh_requests_total\{endpoint="/poh",status="200"} (\d+\.\d+)', metrics_text)
    assert m and float(m.group(1)) >= 2.0
