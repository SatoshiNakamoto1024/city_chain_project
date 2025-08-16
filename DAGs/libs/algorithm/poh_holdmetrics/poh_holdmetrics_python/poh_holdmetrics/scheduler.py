# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\scheduler.py
# -*- coding: utf-8 -*-
"""
非同期スケジューラ

* tracker.snapshot() を定期実行して任意処理（送信など）を行う
* Rust 側に GC API があれば併せて実行
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Callable

from .tracker import AsyncTracker
from .config import settings

_logger = logging.getLogger(__name__)


class Scheduler:
    """
    周期タスクを管理するラッパ。`start()` / `stop()` でライフサイクル制御。
    """

    # ------------------------------------------------------------ #
    # ctor
    # ------------------------------------------------------------ #
    def __init__(
        self,
        tracker: AsyncTracker,
        on_collect: Callable[[list[tuple[str, float]]], None] | None = None,
    ) -> None:
        self.tracker = tracker
        self.on_collect = on_collect or (lambda *_: None)
        self._tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------ #
    # public
    # ------------------------------------------------------------ #
    async def start(self) -> None:
        """collect / gc 2 本のバックグラウンドタスクを起動"""
        if self._tasks:
            return  # already running

        self._stop_event.clear()
        self._tasks.append(asyncio.create_task(self._collect_loop(), name="collect"))
        self._tasks.append(asyncio.create_task(self._gc_loop(), name="gc"))
        _logger.info("Scheduler started with %d tasks", len(self._tasks))

    async def stop(self) -> None:
        """開始済みタスクをすべてキャンセル"""
        self._stop_event.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        _logger.info("Scheduler stopped")

    # ------------------------------------------------------------ #
    # internal loops
    # ------------------------------------------------------------ #
    async def _collect_loop(self) -> None:
        interval = settings.collect_interval
        try:
            while not self._stop_event.is_set():
                stats = self.tracker.snapshot()  # List[(holder, score)]
                self.on_collect(stats)
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
        except asyncio.CancelledError:
            pass

    async def _gc_loop(self) -> None:
        interval = settings.gc_interval
        # Rust Aggregator が gc() API を公開していれば呼び出す
        has_gc = hasattr(self.tracker._agg, "gc")
        try:
            while not self._stop_event.is_set():
                if has_gc:  # type: ignore[attr-defined]
                    self.tracker._agg.gc()  # type: ignore[attr-defined]
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
        except asyncio.CancelledError:
            pass
