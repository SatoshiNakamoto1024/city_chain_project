# D:\city_chain_project\network\DAGs\common\object_processing\test_object_processing.py
"""
E2E テスト: 10 シャード振り分け & ワーカー処理
"""
from __future__ import annotations
import asyncio
import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from object_processing.shard_router import IngressRouter
from object_processing.event import BaseEvent
from object_processing.shard_worker import start_workers
from object_processing.config import SHARD_COUNT


@pytest.mark.asyncio
async def test_shard_dispatch_and_handle():
    router = IngressRouter()
    processed: set[str] = set()

    async def handler(ev: BaseEvent):
        processed.add(ev.event_id)

    # ワーカー起動
    tasks = start_workers(router, handler, concurrency=1)

    # 50 イベント流し込む
    events = [BaseEvent(payload={"i": i}) for i in range(50)]
    for ev in events:
        await router.route(ev)

    # 全キューが空になるまで待つ
    for q in router.queues:
        await q.join()

    # 検証
    assert processed == {ev.event_id for ev in events}

    # ワーカー停止 (キャンセル)
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
