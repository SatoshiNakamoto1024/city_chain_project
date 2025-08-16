# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_api.py
import pytest
from fastapi.testclient import TestClient
from poh_holdmetrics.api.http_server import app
import grpc
import poh_holdmetrics.protocols.hold_pb2 as pb
import poh_holdmetrics.protocols.hold_pb2_grpc as grpc_api
import multiprocessing
import asyncio

client = TestClient(app)

def test_http_hold_and_stats():
    now = "2025-01-01T00:00:00Z"
    payload = {"token_id":"t","holder_id":"h","start":now,"end":now,"weight":1.0}
    r = client.post("/hold", json=payload)
    assert r.status_code == 202
    r2 = client.get("/stats")
    assert r2.status_code == 200

@pytest.mark.asyncio
async def test_grpc_stats_broadcast(grpc_address):  # ← フィクスチャ受け取る
    async with grpc.aio.insecure_channel(grpc_address) as ch:
        stub = grpc_api.HoldMetricsStub(ch)
        stream = stub.Stats(pb.google_dot_protobuf_dot_empty__pb2.Empty())
        stat = await stream.read()
        assert hasattr(stat, "holder_id")