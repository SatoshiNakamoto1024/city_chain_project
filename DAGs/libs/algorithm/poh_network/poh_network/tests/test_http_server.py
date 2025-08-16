# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\tests\test_http_server.py
import asyncio
from aiohttp import ClientSession, web
import pytest
from poh_network.http_server import create_app


@pytest.mark.asyncio
async def test_http_broadcast(tmp_path, unused_tcp_port):
    base = str(tmp_path / "data")
    db   = str(tmp_path / "data/poh.db")
    port = unused_tcp_port

    app = await create_app(base, db)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", port)
    await site.start()

    async with ClientSession() as sess:
        payload = {
            "tx_id": "1",
            "holder_id": "h",
            "timestamp": 0.0,
            "payload":  "cA==",  # base64.b64encode(b"p").decode()
        }
        async with sess.post(f"http://127.0.0.1:{port}/broadcast", json=payload) as r:
            assert r.status == 200

    await runner.cleanup()
