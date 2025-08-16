# D:\city_chain_project\network\DAGs\common\presence\app_resilience.py
"""
app_resilience.py
-----------------
* サーキットブレーカー挙動を確認できる `/unstable`
* レートリミッター挙動を確認できる `/limited`
を提供する FastAPI サーバ。

起動:
    python -m network.DAGs.common.presence.resilience.app_resilience
"""
from __future__ import annotations
import asyncio
import logging
import random
from fastapi import FastAPI, HTTPException, Request
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resilience.circuit_breaker import circuit_breaker, CircuitOpenError
from resilience.rate_limiter import RateLimiter, RateLimitExceeded
from resilience.errors import CircuitOpenError as CBOpen

# ──────────────────────────
# logger
# ──────────────────────────
logger = logging.getLogger("resilience.app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)

# ──────────────────────────
# FastAPI インスタンス
# ──────────────────────────
app = FastAPI(title="Resilience Playground")

# ──────────────────────────
# グローバル RateLimiter
# ──────────────────────────
global_rl = RateLimiter(rate=2, capacity=2)  # 2 req/sec, burst 2

# ──────────────────────────
# Middleware : IP 単位レート制御
# ──────────────────────────
class RLMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        try:
            await global_rl.acquire()
            return await call_next(request)
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="Too Many Requests")

app.add_middleware(RLMiddleware)

# ──────────────────────────
# Circuit Breaker 用 route
# ──────────────────────────
@circuit_breaker(max_failures=3, reset_timeout=2)
async def _maybe_fail():
    # 50% の確率で失敗する擬似 I/O
    await asyncio.sleep(0.05)
    if random.random() < 0.5:
        raise RuntimeError("random failure")

@app.get("/unstable")
async def unstable():
    """
    50% で失敗するエンドポイント。
    3 連続失敗で Circuit OPEN → 2 秒後に HALF-OPEN → 成功で CLOSED。
    """
    try:
        await _maybe_fail()
        return {"status": "ok"}
    except CBOpen:
        raise HTTPException(status_code=503, detail="circuit open")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ──────────────────────────
# RateLimiter 用 route
# ──────────────────────────
@app.get("/limited")
async def limited():
    """
    グローバル RateLimiter (2 req/sec, burst 2) を直接テストする。
    """
    try:
        await global_rl.acquire()
        return {"status": "granted"}
    except RateLimitExceeded:
        raise HTTPException(status_code=429, detail="rate limit")

# ──────────────────────────
# 直接起動
# ──────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8090,
        log_level="info",
    )
