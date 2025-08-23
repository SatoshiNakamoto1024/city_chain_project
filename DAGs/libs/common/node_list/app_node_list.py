# D:\city_chain_project\network\DAGs\common\node_list\app_node_list.py
"""
Presence Service 実装 (FastAPI + Redis backend)
起動:
    python -m common.node_list.app_node_list
環境:
    PRESENCE_BACKEND      ← 依存しない（常に HTTP サーバ）
    PRESENCE_REDIS_URI
    NODELIST_HEARTBEAT_SEC
    PRESENCE_HTTP_PORT
"""
from __future__ import annotations
import time
from typing import List
from redis.asyncio import Redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from node_list.config import (
    PRESENCE_REDIS_URI,
    HEARTBEAT_INTERVAL_SEC,
    PRESENCE_HTTP_PORT,
)

# ────────────────────────────
# 定数
# ────────────────────────────
SET_KEY = "presence:online"
LAST_SEEN = "presence:last_seen:{}"  # node_id → key


# ────────────────────────────
# Pydantic models
# ────────────────────────────
class NodeEvent(BaseModel):
    node_id: str


class NodeInfo(BaseModel):
    node_id: str
    last_seen: float


# ────────────────────────────
# FastAPI & Redis
# ────────────────────────────
app = FastAPI(title="Presence Service")
redis: Redis


@app.on_event("startup")
async def _startup():
    global redis
    redis = Redis.from_url(PRESENCE_REDIS_URI, decode_responses=True)


# ────────────────────────────
# Redis helpers
# ────────────────────────────
async def _login(node_id: str):
    pipe = redis.pipeline()
    pipe.sadd(SET_KEY, node_id)
    pipe.set(LAST_SEEN.format(node_id), time.time(), ex=HEARTBEAT_INTERVAL_SEC * 2)
    await pipe.execute()


async def _logout(node_id: str):
    pipe = redis.pipeline()
    pipe.srem(SET_KEY, node_id)
    pipe.delete(LAST_SEEN.format(node_id))
    await pipe.execute()


async def _heartbeat(node_id: str):
    ok = await redis.exists(LAST_SEEN.format(node_id))
    if not ok:
        raise HTTPException(status_code=404, detail="node not found")
    await redis.set(LAST_SEEN.format(node_id), time.time(), ex=HEARTBEAT_INTERVAL_SEC * 2)


async def _list_nodes() -> List[NodeInfo]:
    node_ids = await redis.smembers(SET_KEY)
    infos: list[NodeInfo] = []
    for nid in node_ids:
        ts = await redis.get(LAST_SEEN.format(nid))
        if ts is not None:
            infos.append(NodeInfo(node_id=nid, last_seen=float(ts)))
    return sorted(infos, key=lambda x: x.node_id)


# ────────────────────────────
# Routes
# ────────────────────────────
@app.get("/presence", response_model=list[NodeInfo])
async def list_presence():
    return await _list_nodes()


@app.post("/presence/login")
async def login(ev: NodeEvent):
    await _login(ev.node_id)
    return {"status": "OK"}


@app.post("/presence/logout")
async def logout(ev: NodeEvent):
    await _logout(ev.node_id)
    return {"status": "OK"}


@app.post("/presence/heartbeat")
async def heartbeat(ev: NodeEvent):
    await _heartbeat(ev.node_id)
    return {"status": "OK"}


# ────────────────────────────
# CLI
# ────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PRESENCE_HTTP_PORT,
        log_level="info",
    )
