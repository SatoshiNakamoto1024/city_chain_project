# D:\city_chain_project\network\DAGs\common\node_list\app_node_list.py
"""
app_node_list.py  ― Presence Service (HTTP + Redis)

エンドポイント
--------------
GET  /presence            -> 全オンラインノード [{node_id, last_seen}]
POST /presence/login      {node_id}
POST /presence/logout     {node_id}
POST /presence/heartbeat  {node_id}

※ TTL 失効は Redis のキー TTL に任せる
"""
from __future__ import annotations

import os
import time
from typing import List

import aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ─────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────
REDIS_URI = os.getenv("PRESENCE_REDIS_URI", "redis://localhost:6379/0")
HEARTBEAT_SEC = int(os.getenv("NODELIST_HEARTBEAT_SEC", 3))
PORT = int(os.getenv("PRESENCE_HTTP_PORT", 8080))

SET_KEY = "presence:online"
LAST_SEEN = "presence:last_seen:{}"  # node_id 埋め込み

# ─────────────────────────────────────────────
# モデル
# ─────────────────────────────────────────────
class NodeEvent(BaseModel):
    node_id: str

class NodeInfo(BaseModel):
    node_id: str
    last_seen: float  # epoch 秒

# ─────────────────────────────────────────────
# APP / Redis
# ─────────────────────────────────────────────
app = FastAPI(title="Presence Service")

redis: aioredis.Redis

@app.on_event("startup")
async def _startup():
    global redis
    redis = aioredis.from_url(REDIS_URI, decode_responses=True)

# ─────────────────────────────────────────────
# ハンドラ
# ─────────────────────────────────────────────
async def _redis_login(node_id: str):
    pipe = redis.pipeline()
    pipe.sadd(SET_KEY, node_id)
    pipe.set(LAST_SEEN.format(node_id), time.time(), ex=HEARTBEAT_SEC * 2)
    await pipe.execute()

async def _redis_logout(node_id: str):
    pipe = redis.pipeline()
    pipe.srem(SET_KEY, node_id)
    pipe.delete(LAST_SEEN.format(node_id))
    await pipe.execute()

async def _redis_heartbeat(node_id: str):
    exists = await redis.exists(LAST_SEEN.format(node_id))
    if not exists:
        raise HTTPException(status_code=404, detail="node not found")
    await redis.expire(LAST_SEEN.format(node_id), HEARTBEAT_SEC * 2)
    await redis.set(LAST_SEEN.format(node_id), time.time())

async def _redis_list() -> List[NodeInfo]:
    node_ids = await redis.smembers(SET_KEY)
    infos: list[NodeInfo] = []
    for nid in node_ids:
        ts = await redis.get(LAST_SEEN.format(nid))
        if ts is not None:
            infos.append(NodeInfo(node_id=nid, last_seen=float(ts)))
    # ソートして返す
    return sorted(infos, key=lambda x: x.node_id)

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/presence", response_model=list[NodeInfo])
async def list_presence():
    return await _redis_list()

@app.post("/presence/login")
async def login(ev: NodeEvent):
    await _redis_login(ev.node_id)
    return {"status": "OK"}

@app.post("/presence/logout")
async def logout(ev: NodeEvent):
    await _redis_logout(ev.node_id)
    return {"status": "OK"}

@app.post("/presence/heartbeat")
async def heartbeat(ev: NodeEvent):
    await _redis_heartbeat(ev.node_id)
    return {"status": "OK"}

# ─────────────────────────────────────────────
# CLI 起動
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app_node_list:app",
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_level="info",
    )
