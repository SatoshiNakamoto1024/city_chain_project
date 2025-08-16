# D:\city_chain_project\network\DAGs\common\object_processing\shard_worker.py
"""
object_processing.shard_worker
------------------------------
各シャード専用の非同期ワーカー
"""
from __future__ import annotations
import asyncio
import logging
from typing import Awaitable, Callable, List
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from object_processing.config import SHARD_COUNT, WORKER_CONCURRENCY
from object_processing.event import BaseEvent
from object_processing.shard_router import IngressRouter

logger = logging.getLogger("common.object_processing.worker")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(h)


# 型: イベントハンドラ
EventHandler = Callable[[BaseEvent], Awaitable[None]]


class ShardWorker:
    """
    1 シャードを担当するワーカーループ
    """

    def __init__(
        self,
        shard_id: int,
        queue: asyncio.Queue[BaseEvent],
        handler: EventHandler,
        name: str | None = None,
    ):
        self._shard_id = shard_id
        self._queue = queue
        self._handler = handler
        self._name = name or f"shard-{shard_id}"

    # ----------------------------------------------
    # メインループ
    # ----------------------------------------------
    async def run(self) -> None:
        logger.info("Worker %s started", self._name)
        while True:
            ev = await self._queue.get()
            try:
                await self._handler(ev)
            except Exception as e:  # pragma: no cover
                logger.exception("Worker %s error: %s", self._name, e)
            finally:
                self._queue.task_done()


# ----------------------------------------------------------
# helper: 全シャード分のワーカーをまとめて起動
# ----------------------------------------------------------
def start_workers(
    router: IngressRouter,
    handler: EventHandler,
    concurrency: int | None = None,
) -> List[asyncio.Task]:
    """
    Example
    -------
    router = IngressRouter()
    async def my_handler(ev): ...
    tasks = start_workers(router, my_handler)
    """
    conc = concurrency or WORKER_CONCURRENCY
    tasks: List[asyncio.Task] = []
    for shard in range(SHARD_COUNT):
        for i in range(conc):
            worker = ShardWorker(
                shard_id=shard,
                queue=router.get_queue(shard),
                handler=handler,
                name=f"shard-{shard}-{i}",
            )
            tasks.append(asyncio.create_task(worker.run()))
    return tasks
