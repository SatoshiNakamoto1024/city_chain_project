# D:\city_chain_project\network\DAGs\common\node_list\manager.py
"""
common.node_list.manager
========================
Presence Service から “オンライン中ノード一覧” を取得・キャッシュし続ける
バックグラウンドタスクを提供する。

バックエンドは 2 種類
--------------------
- redis   : Redis の `SET + TTL` を Presence として利用
- http    : FastAPI 製 Presence Service (common.node_list.app_node_list) の REST API

利用方法
--------
from common.node_list.manager import start_background_manager

# アプリ起動時に一度だけ呼ぶ
start_background_manager()

# 以降、registry からいつでも取得
from common.node_list.registry import get_registry
nodes = await get_registry().get_nodes()
"""
from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import List
import aiohttp
from redis.asyncio import Redis
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from node_list.schemas import NodeInfo
from node_list.config import (
    NODE_ID,
    PRESENCE_BACKEND,
    PRESENCE_REDIS_URI,
    PRESENCE_HTTP_ENDPOINT,
    HEARTBEAT_INTERVAL_SEC,
)
from .registry import get_registry

# ──────────────────────────────────────────
# logger
# ──────────────────────────────────────────
logger = logging.getLogger("common.node_list.manager")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(_h)

# ──────────────────────────────────────────
# Redis backend
# ──────────────────────────────────────────
class _RedisPresence:
    """
    Redis による Presence 実装

    - SET presence:online                … オンライン node_id 集合
    - KEY presence:last_seen:<node_id>   … TTL = 2 * HEARTBEAT
    """

    SET_KEY = "presence:online"
    LAST_SEEN = "presence:last_seen:{}"

    def __init__(self, uri: str):
        self._redis: Redis = Redis.from_url(uri, decode_responses=True)

    # ---------- Presence API ----------
    async def login(self, node_id: str) -> None:
        pipe = self._redis.pipeline()
        pipe.sadd(self.SET_KEY, node_id)
        pipe.set(
            self.LAST_SEEN.format(node_id),
            time.time(),
            ex=HEARTBEAT_INTERVAL_SEC * 2,
        )
        await pipe.execute()

    async def logout(self, node_id: str) -> None:
        pipe = self._redis.pipeline()
        pipe.srem(self.SET_KEY, node_id)
        pipe.delete(self.LAST_SEEN.format(node_id))
        await pipe.execute()

    async def heartbeat(self, node_id: str) -> None:
        await self._redis.set(
            self.LAST_SEEN.format(node_id),
            time.time(),
            ex=HEARTBEAT_INTERVAL_SEC * 2,
        )

    async def list_nodes(self) -> List[NodeInfo]:
        node_ids = await self._redis.smembers(self.SET_KEY)
        now = time.time()
        return [NodeInfo(node_id=nid, last_seen=now) for nid in sorted(node_ids)]

# ──────────────────────────────────────────
# HTTP backend
# ──────────────────────────────────────────
class _HttpPresence:
    """
    REST API 版 Presence Service
    (エンドポイントは app_node_list.py が提供)
    """

    def __init__(self, endpoint: str):
        self._base = endpoint.rstrip("/")
        self._sess = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))

    async def login(self, node_id: str) -> None:
        await self._sess.post(f"{self._base}/login", json={"node_id": node_id})

    async def logout(self, node_id: str) -> None:
        await self._sess.post(f"{self._base}/logout", json={"node_id": node_id})

    async def heartbeat(self, node_id: str) -> None:
        await self._sess.post(f"{self._base}/heartbeat", json={"node_id": node_id})

    async def list_nodes(self) -> List[NodeInfo]:
        async with self._sess.get(self._base) as resp:
            data = await resp.json()
        return [NodeInfo(**d) for d in data]

# ──────────────────────────────────────────
# Manager 本体
# ──────────────────────────────────────────
class NodeListManager:
    """
    `asyncio.create_task(NodeListManager().run_forever())`
    で常駐させる。  
    便利ヘルパ `start_background_manager()` が下にある。
    """

    def __init__(self) -> None:
        # backend 選択
        if PRESENCE_BACKEND == "redis":
            self._backend: _RedisPresence | _HttpPresence = _RedisPresence(
                PRESENCE_REDIS_URI
            )
        elif PRESENCE_BACKEND == "http":
            self._backend = _HttpPresence(PRESENCE_HTTP_ENDPOINT)
        else:
            raise ValueError(f"Unsupported PRESENCE_BACKEND={PRESENCE_BACKEND}")

        self._registry = get_registry()
        self._stop_evt = asyncio.Event()

    # ---------- control ----------
    async def stop(self) -> None:
        self._stop_evt.set()

    async def run_forever(self) -> None:
        """
        1. Presence Service に login
        2. HEARTBEAT_INTERVAL_SEC ごとに
           - heartbeat
           - list_nodes → レジストリ更新
        3. stop() で Presence から logout
        """
        await self._backend.login(NODE_ID)
        logger.info("Presence login OK (%s)", NODE_ID)

        try:
            while not self._stop_evt.is_set():
                await self._backend.heartbeat(NODE_ID)

                # 最新ノードを取得してレジストリへ反映
                nodes = await self._backend.list_nodes()
                await self._registry.update(nodes)

                await asyncio.wait_for(
                    self._stop_evt.wait(), timeout=HEARTBEAT_INTERVAL_SEC
                )

        finally:
            await self._backend.logout(NODE_ID)
            logger.info("Presence logout")

# ──────────────────────────────────────────
# シングルトン起動用ヘルパ
# ──────────────────────────────────────────
_manager_singleton: NodeListManager | None = None

def start_background_manager() -> None:
    """
    アプリ起動時に呼ぶだけで Presence 同期タスクが走る。

    Example
    -------
    start_background_manager()
    """
    global _manager_singleton
    if _manager_singleton is None:
        _manager_singleton = NodeListManager()
        asyncio.create_task(_manager_singleton.run_forever())
