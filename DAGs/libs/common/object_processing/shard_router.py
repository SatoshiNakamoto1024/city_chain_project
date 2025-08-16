# D:\city_chain_project\network\DAGs\common\object_processing\shard_router.py
"""
object_processing.router
------------------------
Ingress で受け取ったイベントを SHARD_COUNT 個の Queue に振り分ける。
"""
from __future__ import annotations
import asyncio
from typing import List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from object_processing.config import SHARD_COUNT
from object_processing.event import BaseEvent


class IngressRouter:
    """
    Usage
    -----
    router = IngressRouter()
    await router.route(event)           # 自動で queue へ put
    queue = router.get_queue(3)         # shard_id=3 の queue
    """

    def __init__(self) -> None:
        self._queues: List[asyncio.Queue[BaseEvent]] = [
            asyncio.Queue(maxsize=10_000) for _ in range(SHARD_COUNT)
        ]

    # ------------------------------------------------------
    # public API
    # ------------------------------------------------------
    async def route(self, event: BaseEvent) -> None:
        shard = event.shard_id()
        await self._queues[shard].put(event)

    def get_queue(self, shard_id: int) -> asyncio.Queue[BaseEvent]:
        return self._queues[shard_id]

    @property
    def queues(self) -> List[asyncio.Queue[BaseEvent]]:
        return self._queues
