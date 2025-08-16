# D:\city_chain_project\DAGs\libs\algorithm\poh_network\poh_network\tests\test_grpc_server.py
import asyncio
import pytest
import grpc.aio
from poh_network.grpc_server import serve
from poh_network.protocols import poh_pb2, poh_pb2_grpc
from contextlib import suppress

@pytest.mark.asyncio
async def test_grpc_roundtrip(tmp_path, unused_tcp_port):
    base = str(tmp_path / "data")
    db   = str(tmp_path / "data/poh.db")
    port = unused_tcp_port

    # サーバ起動
    server_task = asyncio.create_task(serve(port, base, db))
    await asyncio.sleep(0.3)  # サーバ ready 待ち

    # クライアント送信
    async with grpc.aio.insecure_channel(f"localhost:{port}") as chan:
        stub = poh_pb2_grpc.PohServiceStub(chan)
        req  = poh_pb2.Tx(tx_id="1", holder_id="h", timestamp=0.0, payload=b"p")
        ack  = await stub.Broadcast(req, timeout=2.0)
        assert ack.success

    server_task.cancel()
    with suppress(asyncio.CancelledError):
        await server_task
