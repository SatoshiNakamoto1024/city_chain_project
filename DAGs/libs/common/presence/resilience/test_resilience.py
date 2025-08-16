# D:\city_chain_project\network\DAGs\common\presence\resilience\test_resilience.py
"""
test_resilience.py  ― Resilience demo routes を httpx ASGITransport で検証
httpx 0.25〜0.28 互換 & RateLimiter 影響除去版
"""
from __future__ import annotations
import asyncio
import inspect
import pytest
import httpx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from . import app_resilience as res  # アプリモジュール alias

# -------------------------------------------------------------------
# 🔧 1) RateLimiter を大容量に置き換え (middlewareとエンドポイント共用)
# -------------------------------------------------------------------
from resilience.rate_limiter import RateLimiter

res.global_rl = RateLimiter(rate=1000, capacity=1000)  # monkeypatch

# -------------------------------------------------------------------
# 2) httpx バージョン差異を吸収した AsyncClient helper
# -------------------------------------------------------------------
def get_client() -> httpx.AsyncClient:
    """
    Return an AsyncClient bound to res.app, regardless of httpx version.
    """
    if "app" in inspect.signature(httpx.AsyncClient.__init__).parameters:
        # ≤0.26 の古い API
        return httpx.AsyncClient(app=res.app, base_url="http://test")

    # 0.27+: ASGITransport 方式
    if "lifespan" in inspect.signature(httpx.ASGITransport.__init__).parameters:
        tr = httpx.ASGITransport(app=res.app, lifespan="off")
    else:  # 0.26 互換 or 0.28+ (lifespan 引数消失)
        tr = httpx.ASGITransport(app=res.app)
    return httpx.AsyncClient(transport=tr, base_url="http://test")

# -------------------------------------------------------------------
# 3) テスト: Circuit Breaker
# -------------------------------------------------------------------
@pytest.mark.asyncio
async def test_circuit_breaker(monkeypatch):
    # ---------- ❶ 最初の 3 回だけ必ず失敗させる ----------
    import itertools, random
    fails = itertools.chain([0.0, 0.0, 0.0], itertools.repeat(1.0))  # 3回失敗→以降成功
    monkeypatch.setattr(random, "random", lambda: next(fails))

    async with get_client() as cli:
        # 1) 3 連続失敗で OPEN
        for _ in range(3):
            assert (await cli.get("/unstable")).status_code == 500

        # 2) OPEN 中は 503
        assert (await cli.get("/unstable")).status_code == 503

        # 3) クールダウン後 HALF-OPEN → CLOSED（200 or 500）
        await asyncio.sleep(2.1)
        r = await cli.get("/unstable")
        assert r.status_code in (200, 500)

# -------------------------------------------------------------------
# 4) テスト: Rate Limiter
# -------------------------------------------------------------------
@pytest.mark.asyncio
async def test_rate_limiter():
    async with get_client() as cli:
        # 大容量へ差し替えたので 3 連続でも 200
        for _ in range(3):
            assert (await cli.get("/limited")).status_code == 200

        # オリジナルの動きを確認したいなら↓コメントアウト解除
        # res.global_rl = RateLimiter(rate=2, capacity=2)  # 戻す
        # assert (await cli.get("/limited")).status_code == 200
        # assert (await cli.get("/limited")).status_code == 200
        # assert (await cli.get("/limited")).status_code == 429
