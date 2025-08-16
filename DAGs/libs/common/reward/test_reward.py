# D:\city_chain_project\network\DAGs\common\reward\test_reward.py
"""
単体テスト: geo weight と record の検証
"""
from __future__ import annotations
import asyncio
import inspect
import math
import pytest
import httpx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from reward.app_reward import app

# ---------------------------
# httpx クライアント helper
# ---------------------------
def get_cli():
    sig = inspect.signature(httpx.AsyncClient.__init__)
    if "app" in sig.parameters:
        return httpx.AsyncClient(app=app, base_url="http://t")
    tr_sig = inspect.signature(httpx.ASGITransport.__init__)
    tr = httpx.ASGITransport(app=app, lifespan="off") if "lifespan" in tr_sig.parameters \
        else httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=tr, base_url="http://t")

# ---------------------------
# E2E テスト
# ---------------------------
@pytest.mark.asyncio
async def test_reward_flow():
    payload = {
        "holder_id": "node-A",
        "original_tx_id": "tx-1",
        "lat": 35.0, "lon": 139.0,
        "ttl_sec": 7200,
        "tx_holder_lat": 34.0, "tx_holder_lon": 135.0,
        "online_rate": 0.8,
    }
    async with get_cli() as cli:
        assert (await cli.post("/poh_ack", json=payload)).status_code == 200
        res = await cli.get("/score/node-A")
        assert res.status_code == 200
        score = res.json()["score"]
        # スコアは正の値
        assert math.isfinite(score) and score > 0
