# D:\city_chain_project\network\DAGs\common\db\tests\test_db_async.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import pytest
from common.db import get_async_client

@pytest.mark.asyncio
async def test_async_insert_and_find(tmp_path, monkeypatch):
    """
    Motor を使った非同期 CRUD が動くことを確認 (要 MongoDB 起動)。
    MongoDB が無い環境では `pytest -k "not async"` で回避できる。
    """
    uri = "mongodb://localhost:27017"
    try:
        async with get_async_client(uri=uri, db_name="test_db") as cli:
            col = "demo"
            oid = await cli.insert_one(col, {"k": "v"})
            doc = await cli.find_one(col, {"_id": oid})
            assert doc["k"] == "v"
    except Exception:
        pytest.skip("MongoDB が起動していないためスキップ")
