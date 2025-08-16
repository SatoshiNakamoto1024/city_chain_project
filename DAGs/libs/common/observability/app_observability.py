# D:\city_chain_project\network\DAGs\common\observability\app_observability.py
"""
app_observability.py
====================
Prometheus + OpenTelemetry を組み込んだ簡易 FastAPI。

起動:
    python -m network.DAGs.common.observability.app_observability
"""
from __future__ import annotations
import time
import random
from fastapi import FastAPI
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.tracing import init_tracer_provider
from observability.metrics import init_metrics, REQUEST_COUNTER, ACK_COUNTER
from observability.exporters import init_exporters
from observability.middleware import ObservabilityMiddleware

# ──────────────────────────────────────────
# Telemetry 初期化 (必ず最初)
# ──────────────────────────────────────────
init_tracer_provider("observ-demo")

# ──────────────────────────────────────────
# FastAPI アプリ
# ──────────────────────────────────────────
app = FastAPI(title="Observability Demo")
# span 自動付与
app.add_middleware(OpenTelemetryMiddleware)
# 追加メトリクス + span 名補正
app.add_middleware(ObservabilityMiddleware)


@app.get("/ping")
async def ping():
    """最もシンプルなエンドポイント"""
    return {"msg": "pong"}


@app.post("/poh")
async def poh():
    """
    PoH_REQUEST を疑似発行して ACK を返す。
    * メトリクス更新
    * ダミー負荷 (0-100ms)
    """
    REQUEST_COUNTER.labels(endpoint="/poh", status="200").inc()
    await _do_work()
    ACK_COUNTER.labels(endpoint="/poh").inc()
    return {"ack": True}


# 疑似ワーク負荷
async def _do_work():
    dur = random.uniform(0.01, 0.1)
    time.sleep(dur)


# ──────────────────────────────────────────
# Entrypoint
# ──────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,
        log_level="info",
    )
