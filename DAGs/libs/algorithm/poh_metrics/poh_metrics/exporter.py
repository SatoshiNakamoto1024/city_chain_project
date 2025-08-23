# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\exporter.py
# poh_metrics/exporter.py

"""
Prometheus エクスポーター用 HTTP サーバ。

/metrics エンドポイントをシンプルに公開します。
aiohttp を使った非同期サーバです。
"""

import asyncio

from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .registry import get_registry


async def metrics_handler(request: web.Request) -> web.Response:
    """
    /metrics リクエストハンドラ。
    """
    data = generate_latest(get_registry())
    # aiohttp では content_type に charset があると例外になるため headers で指定
    return web.Response(
        body=data,
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )


async def start_http_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    メトリクス専用 HTTP サーバを起動し、キャンセルされるまで待機します。
    """
    app = web.Application()
    app.router.add_get("/metrics", metrics_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    # 永久待機
    await asyncio.Event().wait()
