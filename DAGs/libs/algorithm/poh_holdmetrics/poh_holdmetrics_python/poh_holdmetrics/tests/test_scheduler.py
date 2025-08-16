# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_scheduler.py
import pytest
import asyncio
from poh_holdmetrics.scheduler import Scheduler
from poh_holdmetrics.tracker import AsyncTracker

@pytest.mark.asyncio
async def test_scheduler_start_stop(tmp_path):
    tracker = AsyncTracker()
    sched = Scheduler(tracker)
    await sched.start()
    # 少し待って collect_loop / gc_loop が起動しているかだけ確認
    await asyncio.sleep(0.1)
    await sched.stop()
    # タスクがキャンセルされ例外が返らないこと
