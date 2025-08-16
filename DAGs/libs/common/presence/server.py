# D:\city_chain_project\network\DAGs\common\presence\server.py
"""
common.presence.server
----------------------
FastAPI Presence Service + レート制御ミドルウェア
"""
from __future__ import annotations
import time
from typing import List
from redis.asyncio import Redis
from fastapi import FastAPI, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from presence.resilience.rate_limiter import RateLimiter
from presence.resilience.errors import RateLimitExceeded
from presence.config import (
    PRESENCE_REDIS_URI,
    HEARTBEAT_INTERVAL_SEC,
    PRESENCE_HTTP_PORT,
)
from node_list.schemas import NodeInfo

# ────────────────────────────
# Redis keys
# ────────────────────────────
SET_KEY = "presence:online"
LAST_SEEN = "presence:last_seen:{}"

# ────────────────────────────
# Rate limit middleware (IP 単位)
# ────────────────────────────
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, rate: float, capacity: int):
        super().__init__(app)
        self._limiters: dict[str, RateLimiter] = {}
        self._rate = rate
        self._cap = capacity

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        limiter = self._limiters.setdefault(client_ip, RateLimiter(self._rate, self._cap))
        try:
            await limiter.acquire()
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="Too Many Requests")
        return await call_next(request)

# ────────────────────────────
# FastAPI
# ────────────────────────────
app = FastAPI(title="Presence Service with Resilience")
app.add_middleware(RateLimitMiddleware, rate=30, capacity=60)

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

async def _list() -> List[NodeInfo]:
    ids = await redis.smembers(SET_KEY)
    infos = []
    for nid in ids:
        ts = await redis.get(LAST_SEEN.format(nid))
        if ts:
            infos.append(NodeInfo(node_id=nid, last_seen=float(ts)))
    return infos

# ────────────────────────────
# Routes
# ────────────────────────────
@app.get("/presence", response_model=list[NodeInfo])
async def list_presence():
    return await _list()

@app.post("/presence/login")
async def login(body: dict):
    await _login(body["node_id"])
    return {"status": "OK"}

@app.post("/presence/logout")
async def logout(body: dict):
    await _logout(body["node_id"])
    return {"status": "OK"}

@app.post("/presence/heartbeat")
async def heartbeat(body: dict):
    await _heartbeat(body["node_id"])
    return {"status": "OK"}

# ────────────────────────────
# Entry point
# ────────────────────────────
def create_app() -> FastAPI:  # for uvicorn programmatic launch
    return app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PRESENCE_HTTP_PORT, log_level="info")
