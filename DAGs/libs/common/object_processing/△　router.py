# D:\city_chain_project\network\DAGs\common\object_processing\shard_router.py
import asyncio
import hashlib
from typing import List
from .event import ObjectEvent

NUM_SHARDS = 10

class Router:
    def __init__(self):
        self.ingress: asyncio.Queue[ObjectEvent] = asyncio.Queue()
        self.queues: List[asyncio.Queue[ObjectEvent]] = [
            asyncio.Queue() for _ in range(NUM_SHARDS)
        ]

    async def start(self):
        """バックグラウンドでルーティングを動かす"""
        asyncio.create_task(self._route_loop())

    async def _route_loop(self):
        while True:
            evt = await self.ingress.get()
            # object_id の SHA256 を数値化して 0..9 に割り振る
            h = int(hashlib.sha256(evt.object_id.encode()).hexdigest(), 16)
            idx = h % NUM_SHARDS
            await self.queues[idx].put(evt)
            self.ingress.task_done()
