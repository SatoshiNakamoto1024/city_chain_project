# D:\city_chain_project\DAGs\libs\algorithm\poh_metrics\poh_metrics\tests\test_exporter.py
import pytest
import asyncio
from aiohttp import ClientSession
from poh_metrics.exporter import start_http_server

@pytest.mark.asyncio
async def test_exporter_endpoint(unused_tcp_port):
    port = unused_tcp_port
    # サーバ起動
    task = asyncio.create_task(start_http_server("127.0.0.1", port))
    await asyncio.sleep(0.1)  # ready 待ち

    async with ClientSession() as sess:
        resp = await sess.get(f"http://127.0.0.1:{port}/metrics")
        text = await resp.text()
        assert resp.status == 200
        assert "poh_issued_total" in text

    # キャンセル＆例外確認
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
