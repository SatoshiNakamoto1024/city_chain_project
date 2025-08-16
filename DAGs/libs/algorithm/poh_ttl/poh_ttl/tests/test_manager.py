# D:\city_chain_project\DAGs\libs\algorithm\poh_ttl\poh_ttl\tests\test_manager.py
import pytest
import time
import asyncio

from poh_ttl.manager import TTLManager
from poh_storage.storage import StorageManager
from poh_storage.types   import Tx
from poh_ttl.exceptions  import TTLManagerError

@pytest.mark.asyncio
async def test_scan_once(tmp_path):
    base = tmp_path / "data"
    db   = tmp_path / "data" / "poh.db"

    sm = await StorageManager.create(str(base), str(db))
    try:
        # TTL=2秒
        ttl = TTLManager(sm, ttl_seconds=2)
        # 現在時刻で保存
        tx = Tx(tx_id="1", holder_id="h", timestamp=time.time(), payload=b"p")
        await sm.save_tx(tx)

        # 1秒後→削除されない
        await asyncio.sleep(1)
        expired = await ttl.scan_once()
        assert expired == []

        # さらに2秒待って→削除される
        await asyncio.sleep(2.1)
        expired = await ttl.scan_once()
        assert expired == ["1"]

    finally:
        await sm.close()
