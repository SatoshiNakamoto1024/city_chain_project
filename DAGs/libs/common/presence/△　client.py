# D:\city_chain_project\network\DAGs\common\presence\client.py
"""
common.presence.client
----------------------
Presence Service を呼び出す高レベルクライアント
- CircuitBreaker と RateLimiter を組み込み
"""

from __future__ import annotations
import aiohttp
import logging
from typing import List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from presence.resilience.circuit_breaker import circuit_breaker
from presence.resilience.rate_limiter import RateLimiter
from presence.resilience.errors import CircuitOpenError, RateLimitExceeded
from node_list.schemas import NodeInfo  # 再利用

logger = logging.getLogger("common.presence.client")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)


class PresenceClient:
    """
    Parameters
    ----------
    base_url : str
        Presence Service のベース URL（例: http://localhost:8080/presence）
    """

    def __init__(self, base_url: str):
        self._base = base_url.rstrip("/")
        self._sess = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))
        # レジリエンス
        self._breaker = circuit_breaker(max_failures=5, reset_timeout=15)
        self._limiter = RateLimiter(rate=10, capacity=20)

    # --------------------------------------------------
    # wrapped HTTP calls
    # --------------------------------------------------
    async def _post(self, path: str, json: dict):
        await self._limiter.acquire()
        url = f"{self._base}{path}"
        async with self._sess.post(url, json=json) as resp:
            resp.raise_for_status()

    async def _get(self, path: str):
        await self._limiter.acquire()
        url = f"{self._base}{path}"
        async with self._sess.get(url) as resp:
            resp.raise_for_status()
            return await resp.json()

    # --------------------------------------------------
    # public API
    # --------------------------------------------------
    async def login(self, node_id: str):
        await self._post("/login", {"node_id": node_id})

    async def logout(self, node_id: str):
        await self._post("/logout", {"node_id": node_id})

    async def heartbeat(self, node_id: str):
        await self._post("/heartbeat", {"node_id": node_id})

    @circuit_breaker(max_failures=3, reset_timeout=10)
    async def list_nodes(self) -> List[NodeInfo]:
        try:
            data = await self._get("")
            return [NodeInfo(**d) for d in data]
        except (CircuitOpenError, RateLimitExceeded):
            raise
        except Exception as e:
            logger.warning("list_nodes error: %s", e)
            raise
