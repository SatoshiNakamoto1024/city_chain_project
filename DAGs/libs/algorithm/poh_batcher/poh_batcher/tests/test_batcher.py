# D:\city_chain_project\DAGs\libs\algorithm\poh_batcher\poh_batcher\tests\test_batcher.py
import pytest
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from poh_batcher.batcher import Batcher
from poh_batcher.types import AckItem


@pytest.mark.asyncio
async def test_batcher_splits_on_size(tmp_path):
    out_dir = tmp_path / "batches"
    batcher = Batcher(batch_size=3, batch_timeout=0.5, output_dir=str(out_dir))
    await batcher.start()

    # 5 件を submit → size=3, size=2 の2ファイルになるはず
    items = [
        AckItem(
            id=str(i),
            timestamp=datetime.now(timezone.utc).isoformat(),
            signature="sig",
            pubkey="pk",
        )
        for i in range(5)
    ]
    for it in items:
        await batcher.submit(it)

    # バッチタイムアウトが来るまで待機
    await asyncio.sleep(0.6)
    await batcher.stop()

    files = sorted(os.listdir(out_dir))
    assert len(files) == 2

    # 中身チェック
    f1 = out_dir / files[0]
    data1 = json.loads(f1.read_text(encoding="utf-8"))
    assert len(data1["items"]) == 3

    f2 = out_dir / files[1]
    data2 = json.loads(f2.read_text(encoding="utf-8"))
    assert len(data2["items"]) == 2


@pytest.mark.asyncio
async def test_batcher_flush_on_shutdown(tmp_path):
    out_dir = tmp_path / "batches"
    batcher = Batcher(batch_size=10, batch_timeout=5.0, output_dir=str(out_dir))
    await batcher.start()

    # 少量だけ submit
    ack = AckItem(
        id="only1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        signature="sig",
        pubkey="pk",
    )
    await batcher.submit(ack)

    # 即座に stop を呼び出す
    await batcher.stop()

    files = sorted(os.listdir(out_dir))
    assert len(files) == 1
    data = json.loads((out_dir / files[0]).read_text(encoding="utf-8"))
    assert data["items"][0]["id"] == "only1"
