# D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_python\poh_holdmetrics\tests\test_tracker.py
import pytest
import asyncio
from datetime import datetime, timedelta
from poh_holdmetrics.tracker import AsyncTracker
from poh_holdmetrics.data_models import HoldEvent

@pytest.mark.asyncio
async def test_tracker_basic():
    t = AsyncTracker()
    now = datetime.utcnow()
    ev = HoldEvent(token_id="a", holder_id="h", start=now, end=now + timedelta(seconds=5), weight=2.0)
    await t.record(ev)
    stats = t.snapshot()
    assert stats == [("h", pytest.approx(10.0))]  # 5s * weight=2
