# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tests\test_storage.py
import pytest
from poh_storage.storage import StorageManager
from poh_storage.types import Tx

@pytest.mark.asyncio
async def test_storage_manager(tmp_path):
    base = tmp_path / "data"
    db   = tmp_path / "data" / "poh.db"
    sm   = await StorageManager.create(str(base), str(db))
    try:
        # 保存→一覧→リカバリの一連フロー
        tx = Tx(tx_id="1", holder_id="h", timestamp=0.0, payload=b"payload")
        await sm.save_tx(tx)

        ids = await sm.list_txs()
        assert "1" in ids

        valid = await sm.recover()
        assert "1" in valid
    finally:
        # StorageManager の後片付け
        await sm.close()
