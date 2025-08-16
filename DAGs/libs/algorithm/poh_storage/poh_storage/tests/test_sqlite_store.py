# D:\city_chain_project\DAGs\libs\algorithm\poh_storage\poh_storage\tests\test_sqlite_store.py
import pytest
from poh_storage.sqlite_store import SQLiteStore

@pytest.mark.asyncio
async def test_sqlite_store(tmp_path):
    db = tmp_path / "test.db"
    store = SQLiteStore(str(db))
    await store.init()
    try:
        # CRUD 操作検証
        await store.save("tx1", "hash1", 1.23)
        row = await store.load("tx1")
        assert row == ("hash1", 1.23)
        ids = await store.list_ids()
        assert "tx1" in ids
        await store.remove("tx1")
        assert await store.load("tx1") is None
    finally:
        # aiosqlite コネクションを閉じ、ThreadPoolExecutor をシャットダウン
        conn = getattr(store, "_conn", None)
        if conn:
            await conn.close()
        # asyncio のデフォルト executor もクローズ
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.shutdown_default_executor()
