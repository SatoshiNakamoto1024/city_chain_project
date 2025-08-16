# D:\city_chain_project\DAGs\libs\algorithm\poh_config\poh_config\tests\test_watchers.py
# poh_config/tests/test_watchers.py
import pytest
import asyncio
from pathlib import Path
from poh_config.watchers import watch_file

@pytest.mark.asyncio
async def test_watch_file(tmp_path):
    p = tmp_path / "conf.yaml"
    p.write_text("MIN_POH_REQUIRED: 1\nTTL_SECONDS: 2.0", encoding="utf-8")

    events = []
    async def on_change(data):
        events.append(data)

    # watcher をバックグラウンド起動
    task = asyncio.create_task(watch_file(p, on_change))
    await asyncio.sleep(0.1)

    # ファイル更新
    p.write_text("MIN_POH_REQUIRED: 9\nTTL_SECONDS: 8.8", encoding="utf-8")
    # 監視反映待ち
    await asyncio.sleep(0.5)

    assert events, "on_change が呼び出されていない"
    assert events[-1]["MIN_POH_REQUIRED"] == 9
    assert events[-1]["TTL_SECONDS"] == 8.8

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
