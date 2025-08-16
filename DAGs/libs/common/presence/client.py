# D:\city_chain_project\network\DAGs\common\presence\client.py
"""
common.presence.client
----------------------
Presence Service を呼び出す高レベルクライアント
aiohttp / httpx のどちらでも動作するように実装。
"""
from __future__ import annotations
import logging
from typing import List, Optional

import aiohttp
import httpx
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from presence.config import NODE_ID
from presence.resilience.circuit_breaker import circuit_breaker
from presence.resilience.rate_limiter import RateLimiter
from presence.resilience.errors import CircuitOpenError, RateLimitExceeded
from node_list.schemas import NodeInfo  # 再利用


logger = logging.getLogger(__name__)
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
        末尾 `/presence` を含むベース URL
    session : Optional[aiohttp.ClientSession | httpx.AsyncClient]
        既存のセッションを注入したい場合。省略時は aiohttp を生成。
    """

    def __init__(self, base_url: str, session: Optional[object] = None):
        self._base = base_url.rstrip("/")
        if session is None:
            # デフォルトは aiohttp
            session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))
        self._sess = session

        # レジリエンス
        self._limiter = RateLimiter(rate=10, capacity=20)

    # ==============================================================
    # 内部 HTTP ラッパー：aiohttp / httpx を自動判別
    # ==============================================================

    async def _http_post(self, path: str, json: dict):
        """POST ラッパー: レート制限 + 失敗時例外変換"""
        await self._limiter.acquire()
        url = f"{self._base}{path}"

        # --- aiohttp ---
        if isinstance(self._sess, aiohttp.ClientSession):
            async with self._sess.post(url, json=json) as resp:
                resp.raise_for_status()
                return await resp.json()

        # --- httpx ---
        elif isinstance(self._sess, httpx.AsyncClient):
            resp = await self._sess.post(url, json=json)
            resp.raise_for_status()
            return resp.json()

        else:  # pragma: no cover
            raise TypeError("Unsupported session type")

    async def _http_get(self, path: str):
        await self._limiter.acquire()
        url = f"{self._base}{path}"

        if isinstance(self._sess, aiohttp.ClientSession):
            async with self._sess.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()

        elif isinstance(self._sess, httpx.AsyncClient):
            resp = await self._sess.get(url)
            resp.raise_for_status()
            return resp.json()

        else:  # pragma: no cover
            raise TypeError("Unsupported session type")

    # ==============================================================
    # 公開 API
    # ==============================================================

    async def login(self, node_id: str = NODE_ID):
        await self._http_post("/login", {"node_id": node_id})

    async def logout(self, node_id: str = NODE_ID):
        await self._http_post("/logout", {"node_id": node_id})

    async def heartbeat(self, node_id: str = NODE_ID):
        await self._http_post("/heartbeat", {"node_id": node_id})

    @circuit_breaker(max_failures=3, reset_timeout=10)
    async def list_nodes(self) -> List[NodeInfo]:
        try:
            data = await self._http_get("")
            return [NodeInfo(**d) for d in data]
        except (CircuitOpenError, RateLimitExceeded):
            raise
        except Exception as e:
            logger.warning("list_nodes error: %s", e)
            raise
